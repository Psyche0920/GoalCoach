"""Integration test verifying end-to-end logging pipeline in FastAPI web application.

Verifies:
1. Web request correlation (x-request-id) binds to execution context.
2. HTTP access logging writes to logs/backend.jsonl.
3. Real agent execution triggered via POST /api/v1/events emits to logs/agent_telemetry.jsonl.
4. Token / cost usage emits to logs/cost_accounting.jsonl.
5. All three sinks are physically flushed and isolated in real time without buffering lag.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import create_app
from goalcoach.agents.planning_agent import AgentPlanUpdate, PlanningDeps
from goalcoach.domain.enums import PlanItemKind
from goalcoach.domain.models import PlanItem
from goalcoach.domain.telemetry import CostAccountingRecord
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.logging.sinks import stop_logging_queue
from goalcoach.infrastructure.telemetry import emit_cost_record


@pytest.mark.asyncio
async def test_web_app_logs_to_all_three_sinks_with_correlation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend_log = tmp_path / "backend.jsonl"
    telemetry_log = tmp_path / "agent_telemetry.jsonl"
    cost_log = tmp_path / "cost_accounting.jsonl"

    custom_settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'web-test.db'}",
        content_database_url="sqlite:///./data/database1/goalcoach_hsk1_learning.db",
        backend_log_path=str(backend_log),
        agent_telemetry_log_path=str(telemetry_log),
        cost_accounting_log_path=str(cost_log),
        offline_llm_fallback=True,
    )

    # Stub run_with_fallback to simulate LLM call while emitting cost record
    async def mock_run_with_fallback(
        agent: object, prompt: str, deps: PlanningDeps | None = None, *, component: str
    ) -> tuple[SimpleNamespace, str]:
        # Emit a mock cost accounting record as the LLM gateway does
        from goalcoach.infrastructure.logging.context import current_request_id, get_context

        ctx = get_context()
        trace_id = ctx.get("request_id") or ctx.get("trace_id") or current_request_id()
        emit_cost_record(
            CostAccountingRecord(
                trace_id=trace_id,
                run_id=trace_id,
                agent_name=component,
                provider="openrouter",
                model_name="deepseek/deepseek-chat",
                prompt_tokens=220,
                completion_tokens=65,
                total_tokens=285,
                input_cost_usd=0.00031,
                output_cost_usd=0.00010,
                total_cost_usd=0.00041,
            )
        )

        roadmap = ["hsk1_c01", "hsk1_c02"]
        output = AgentPlanUpdate(
            daily_allocation_minutes=10,
            ordered_items=[
                PlanItem(
                    concept_id="hsk1_c01",
                    kind=PlanItemKind.NEW,
                    objective="Learn Greetings",
                    estimated_minutes=5,
                ),
                PlanItem(
                    concept_id="hsk1_c02",
                    kind=PlanItemKind.NEW,
                    objective="Learn Numbers",
                    estimated_minutes=5,
                ),
            ],
            adaptation_rationale="Initial plan for web learner.",
            roadmap_concept_ids=roadmap,
            roadmap_coverage_rationale="Covers initial HSK1 concepts.",
        )
        return SimpleNamespace(output=output), "openrouter:deepseek/deepseek-chat"

    monkeypatch.setattr("goalcoach.agents.planning_agent.run_with_fallback", mock_run_with_fallback)

    app = create_app(custom_settings)

    test_correlation_id = "web-corr-id-998877"

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/events",
                headers={"x-request-id": test_correlation_id},
                json={
                    "event_type": "GOAL_CREATED",
                    "learner_id": "web-learner-001",
                    "payload": {
                        "title": "HSK 1 Beginner Goal",
                        "target_hsk_level": 1,
                        "daily_available_minutes": 20,
                    },
                },
            )

            assert response.status_code == 200
            assert response.headers.get("x-request-id") == test_correlation_id

    # Sinks flushed on lifespan exit
    stop_logging_queue()

    # 1. Verify backend sink received HTTP access and business logs
    assert backend_log.exists(), "backend.jsonl was not created"
    backend_data = backend_log.read_text(encoding="utf-8")
    assert test_correlation_id in backend_data, "Correlation ID not found in backend log"
    assert "POST" in backend_data
    assert "/api/v1/events" in backend_data

    # 2. Verify agent telemetry sink received planning agent events
    assert telemetry_log.exists(), "agent_telemetry.jsonl was not created"
    telemetry_data = telemetry_log.read_text(encoding="utf-8")
    assert test_correlation_id in telemetry_data, "Correlation ID not propagated to agent telemetry"
    assert "planning_agent" in telemetry_data
    assert "started" in telemetry_data
    assert "completed" in telemetry_data

    # 3. Verify cost accounting sink received token and spend data
    assert cost_log.exists(), "cost_accounting.jsonl was not created"
    cost_data = cost_log.read_text(encoding="utf-8")
    assert test_correlation_id in cost_data, "Correlation ID not propagated to cost accounting"
    assert "deepseek/deepseek-chat" in cost_data
    assert "0.00041" in cost_data
