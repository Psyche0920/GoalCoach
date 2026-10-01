"""Unit tests verifying strict log isolation between operational, telemetry, and cost sinks."""

from __future__ import annotations

import logging
from pathlib import Path

from goalcoach.domain.telemetry import (
    AgentLifecycleStage,
    AgentTelemetryRecord,
    CostAccountingRecord,
)
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.logging.sinks import (
    setup_isolated_sinks,
    start_logging_queue,
    stop_logging_queue,
)
from goalcoach.infrastructure.telemetry import (
    emit_cost_record,
    emit_telemetry_record,
)


def test_logger_propagation_flags(tmp_path: Path) -> None:
    """Verify telemetry and cost loggers have propagate=False to prevent backend pollution."""
    settings = Settings(
        backend_log_path=str(tmp_path / "backend.jsonl"),
        agent_telemetry_log_path=str(tmp_path / "agent_telemetry.jsonl"),
        cost_accounting_log_path=str(tmp_path / "cost_accounting.jsonl"),
    )
    _ = setup_isolated_sinks(settings=settings)

    telemetry_logger = logging.getLogger("goalcoach.agent.telemetry")
    cost_logger = logging.getLogger("goalcoach.agent.cost")

    assert telemetry_logger.propagate is False
    assert cost_logger.propagate is False


def test_zero_cross_sink_pollution(tmp_path: Path) -> None:
    """Verify records emitted to each sink never cross-pollinate into other sinks."""
    backend_file = tmp_path / "backend.jsonl"
    telemetry_file = tmp_path / "agent_telemetry.jsonl"
    cost_file = tmp_path / "cost_accounting.jsonl"

    settings = Settings(
        backend_log_path=str(backend_file),
        agent_telemetry_log_path=str(telemetry_file),
        cost_accounting_log_path=str(cost_file),
    )
    setup_isolated_sinks(settings=settings)
    start_logging_queue()

    try:
        # 1. Log operational backend message
        backend_logger = logging.getLogger("goalcoach.backend")
        backend_logger.info("Operational backend startup", extra={"extra": {"component": "server"}})

        # 2. Emit Agent Telemetry record
        emit_telemetry_record(
            AgentTelemetryRecord(
                trace_id="test-trace-123",
                run_id="test-run-456",
                agent_name="planning_agent",
                stage=AgentLifecycleStage.STARTED,
                metadata={"test_field": "telemetry_only"},
            )
        )

        # 3. Emit Cost record
        emit_cost_record(
            CostAccountingRecord(
                trace_id="test-trace-123",
                run_id="test-run-456",
                agent_name="teaching_agent",
                provider="openrouter",
                model_name="deepseek/deepseek-chat",
                prompt_tokens=150,
                completion_tokens=42,
                total_tokens=192,
                input_cost_usd=0.00021,
                output_cost_usd=0.00007,
                total_cost_usd=0.00028,
            )
        )
    finally:
        stop_logging_queue()

    # Read back all 3 files
    backend_content = backend_file.read_text(encoding="utf-8") if backend_file.exists() else ""
    telemetry_content = (
        telemetry_file.read_text(encoding="utf-8") if telemetry_file.exists() else ""
    )
    cost_content = cost_file.read_text(encoding="utf-8") if cost_file.exists() else ""

    # Verify backend sink contains only backend records
    assert "Operational backend startup" in backend_content
    assert "test_field" not in backend_content
    assert "deepseek-chat" not in backend_content
    assert "total_tokens" not in backend_content

    # Verify telemetry sink contains only telemetry records
    assert "test-trace-123" in telemetry_content
    assert "planning_agent" in telemetry_content
    assert "started" in telemetry_content
    assert "Operational backend startup" not in telemetry_content
    assert "deepseek-chat" not in telemetry_content

    # Verify cost sink contains only cost records
    assert "deepseek-chat" in cost_content
    assert "0.00028" in cost_content
    assert "192" in cost_content
    assert "Operational backend startup" not in cost_content
    assert "test_field" not in cost_content
