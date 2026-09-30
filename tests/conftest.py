import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace

os.environ["GOALCOACH_OFFLINE_LLM_FALLBACK"] = "true"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.dependencies import (
    get_grader_component,
    get_planning_worker,
    get_teaching_worker,
)
from apps.api.main import create_app
from goalcoach.agents.planning_agent import AgentPlanUpdate, PlanningDeps
from goalcoach.domain.enums import PlanItemKind
from goalcoach.domain.models import PlanItem
from goalcoach.infrastructure.config import Settings
from tests.fakes import FakeGraderComponent, FakePlanningWorker, FakeTeachingWorker


@pytest.fixture
def planning_model_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep workflow tests offline while exercising the real planning worker."""

    async def run(
        agent: object, prompt: str, deps: PlanningDeps, *, component: str
    ) -> tuple[SimpleNamespace, str]:
        state = deps.state
        roadmap = state.roadmap_concept_ids or [
            concept.concept_id
            for concept in deps.content_service.list_all_concepts(max_hsk_level=1)
        ]
        required = [
            cid
            for cid, count in sorted(
                state.remediation_counters.items(), key=lambda item: item[1], reverse=True
            )
            if count >= 2 and cid in roadmap
        ]
        unavailable = set(state.today_studied_concept_ids) | set(state.today_remediated_concept_ids)
        candidates = required + [
            cid for cid in roadmap if cid not in unavailable and cid not in required
        ]
        output = AgentPlanUpdate(
            daily_allocation_minutes=20,
            ordered_items=[
                PlanItem(
                    concept_id=cid,
                    kind=PlanItemKind.REMEDIAL if cid in required else PlanItemKind.NEW,
                    objective=f"Practice {cid}",
                    estimated_minutes=5,
                )
                for cid in candidates[:4]
            ],
            adaptation_rationale="Test model prioritizes unresolved remediation.",
            roadmap_concept_ids=roadmap,
            roadmap_coverage_rationale="Test roadmap covers the HSK1 curriculum.",
        )
        return SimpleNamespace(output=output), "test-model"

    monkeypatch.setattr("goalcoach.agents.planning_agent.run_with_fallback", run)


@pytest.fixture(scope="session", autouse=True)
def ensure_curriculum_db_initialized() -> None:
    """Ensure canonical SQLite Database #1 is seeded before any tests run."""
    db_path = Path("data/database1/goalcoach_hsk1_learning.db")
    sql_path = Path(
        "data/database1/GoalCoach_HSK1_Learning_DB_Package/data/goalcoach_hsk1_learning_db_sqlite.sql"
    )

    need_init = True
    if db_path.exists() and db_path.stat().st_size > 0:
        if sql_path.exists() and sql_path.stat().st_mtime > db_path.stat().st_mtime:
            need_init = True
        else:
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT count(*) FROM curriculum_concepts")
                    if cursor.fetchone()[0] > 0:
                        need_init = False
            except (sqlite3.Error, OSError):
                need_init = True

    if need_init and sql_path.exists():
        if db_path.exists():
            db_path.unlink()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sql_path, encoding="utf-8") as f:
            sql_script = f.read()
        with sqlite3.connect(db_path) as conn:
            conn.executescript(sql_script)


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> AsyncClient:
    application = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite:///{tmp_path / 'api-test.db'}",
            content_database_url="sqlite:///./data/database1/goalcoach_hsk1_learning.db",
        )
    )
    application.dependency_overrides[get_planning_worker] = FakePlanningWorker
    application.dependency_overrides[get_teaching_worker] = FakeTeachingWorker
    application.dependency_overrides[get_grader_component] = FakeGraderComponent
    async with application.router.lifespan_context(application):
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
