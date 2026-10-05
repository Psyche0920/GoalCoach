"""Unit and integration tests for FastAPI learning endpoints."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Never

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from apps.api.dependencies import get_planning_worker, get_teaching_worker
from apps.api.main import create_app
from goalcoach.agents.planning_agent import PlanningWorker
from goalcoach.agents.teaching_agent import TeachingDeps, TeachingWorker
from goalcoach.domain.enums import TeachingActionKind
from goalcoach.domain.models import TeachingAction
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.persistence.content_service import ContentService

pytestmark = pytest.mark.usefixtures("planning_model_stub", "teaching_model_stub")


@dataclass(frozen=True, slots=True)
class TeachingModelResult:
    output: TeachingAction


@pytest.fixture
def teaching_model_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace model I/O while keeping exercise selection and real grading active."""

    async def run(
        agent: object, prompt: str, deps: TeachingDeps, *, component: str
    ) -> tuple[TeachingModelResult, str]:
        return TeachingModelResult(
            output=TeachingAction(
                action_kind=TeachingActionKind.EXPLANATION,
                concept_id=deps.concept_id,
                content="Use the curriculum example to practice this concept.",
                history_summary="Introduced the concept using its canonical curriculum example.",
            )
        ), "test-model"

    async def unexpected_grading_model_call(
        agent: object, prompt: str, deps: None, *, component: str
    ) -> Never:
        pytest.fail("Canonical answers must use the real deterministic grading path")

    monkeypatch.setattr("goalcoach.agents.teaching_agent.run_with_fallback", run)
    monkeypatch.setattr(
        "goalcoach.agents.grader_component.run_with_fallback", unexpected_grading_model_call
    )


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    settings = Settings(
        _env_file=None,
        environment="testing",
        database_url=f"sqlite:///{tmp_path / 'learning-api.db'}",
        content_database_url="sqlite:///./data/database1/goalcoach_hsk1_learning.db",
        log_to_file=False,
    )
    application = create_app(settings)

    def planning_worker() -> PlanningWorker:
        return PlanningWorker()

    def teaching_worker() -> TeachingWorker:
        return TeachingWorker()

    application.dependency_overrides[get_planning_worker] = planning_worker
    application.dependency_overrides[get_teaching_worker] = teaching_worker
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    # ASGITransport does not start lifespan; without it dependencies use the working database.
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_curriculum_concepts(client: AsyncClient) -> None:
    res = await client.get("/api/v1/curriculum/concepts")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 120
    # Check camelCase keys
    first = data[0]
    assert "conceptId" in first
    assert "hskLevel" in first
    assert "titleZh" in first


@pytest.mark.asyncio
async def test_curriculum_concepts_level_filter(client: AsyncClient) -> None:
    res = await client.get("/api/v1/curriculum/concepts?level=2")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(c["hskLevel"] == 2 for c in data)


@pytest.mark.asyncio
async def test_curriculum_concept_details(client: AsyncClient) -> None:
    # Fetch list first to get valid conceptId
    list_res = await client.get("/api/v1/curriculum/concepts")
    concept_id = list_res.json()[0]["conceptId"]

    res = await client.get(f"/api/v1/curriculum/concepts/{concept_id}")
    assert res.status_code == 200
    data = res.json()
    assert "concept" in data
    assert "cards" in data
    assert "exercises" in data
    assert data["concept"]["conceptId"] == concept_id


@pytest.mark.asyncio
async def test_learner_aggregate_and_routing(client: AsyncClient) -> None:
    learner_id = "test_learner_001"
    res = await client.get(f"/api/v1/learners/{learner_id}")
    assert res.status_code == 200
    data = res.json()
    assert "state" in data
    assert "overallProgress" in data
    assert "progressSummary" in data
    assert data["state"]["learnerId"] == learner_id


@pytest.mark.asyncio
async def test_today_plan_generation(client: AsyncClient) -> None:
    learner_id = "test_learner_plan_001"
    await client.post(
        "/api/v1/events",
        json={
            "event_type": "GOAL_CREATED",
            "learner_id": learner_id,
            "payload": {"title": "HSK 1", "daily_available_minutes": 20},
        },
    )
    res = await client.get(f"/api/v1/learners/{learner_id}/today-plan")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("replace_exercise", [False, True], ids=["canonical", "generated-matching"])
async def test_submit_answer_via_events(
    client: AsyncClient, app: FastAPI, replace_exercise: bool
) -> None:
    learner_id = "test_learner_001"
    goal_res = await client.post(
        "/api/v1/events",
        json={
            "event_type": "GOAL_CREATED",
            "learner_id": learner_id,
            "payload": {"title": "HSK 1", "daily_available_minutes": 20},
        },
    )
    assert goal_res.status_code == 200
    session_res = await client.post(
        "/api/v1/events",
        json={
            "event_type": "SESSION_STARTED",
            "learner_id": learner_id,
            "payload": {},
        },
    )
    assert session_res.status_code == 200
    action = session_res.json()["teachingAction"]
    concept_id = action["conceptId"]
    if replace_exercise:
        help_res = await client.post(
            "/api/v1/events",
            json={
                "event_type": "HELP_REQUESTED",
                "learner_id": learner_id,
                "payload": {
                    "concept_id": concept_id,
                    "current_exercise_id": action["exercisePayload"]["exercise_id"],
                },
            },
        )
        assert help_res.status_code == 200
        action = help_res.json()["teachingAction"]

    exercise_id = action["exercisePayload"]["exercise_id"]
    assert exercise_id.endswith("_match_auto") is replace_exercise
    assert "accepted_answers" not in action["exercisePayload"]
    assert "answer" not in action["exercisePayload"]

    # Generated matching exercises are service-backed, not rows in the curriculum endpoint.
    content_service = ContentService(app.state.content_repository)
    exercise = content_service.get_exercise(exercise_id)
    assert exercise is not None
    assert exercise.concept_id == concept_id
    accepted = (
        exercise.accepted_answers[0] if exercise.accepted_answers else exercise.answer["value"]
    )
    assert isinstance(accepted, str) and accepted

    submission_payload = {
        "event_type": "ANSWER_SUBMITTED",
        "learner_id": learner_id,
        "payload": {
            "exercise_id": exercise_id,
            "concept_id": concept_id,
            "answer": accepted,
        },
    }
    res = await client.post("/api/v1/events", json=submission_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["gradingResult"] is not None
    assert data["gradingResult"]["passedGates"] is True
    assert data["gradingResult"]["graderVersion"] == (
        "deterministic-matching" if replace_exercise else "deterministic-fast-path"
    )
    assert exercise_id in data["state"]["todayCompletedExerciseIds"]

    saved_res = await client.get(f"/api/v1/learners/{learner_id}")
    assert saved_res.status_code == 200
    assert exercise_id in saved_res.json()["state"]["todayCompletedExerciseIds"]


@pytest.mark.asyncio
async def test_legacy_answers_route_returns_404(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/answers",
        json={
            "learnerId": "test_learner_001",
            "exerciseId": "ex_dummy",
            "answer": "你好",
        },
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_grade_freeform(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/grade-freeform",
        json={"userInput": "我想喝茶", "blueprintId": "bp_test"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_learning_events(client: AsyncClient) -> None:
    payload = {
        "learnerId": "test_learner_001",
        "planItemId": "item_test",
        "conceptIds": ["c_test"],
        "eventType": "output",
        "activeSeconds": 45,
        "engagementScore": 1.0,
    }
    res = await client.post("/api/v1/learning-events", json=payload)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_complete_concept(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/learners/test_learner_001/complete-concept",
        json={"conceptId": "c_test_complete", "score": 100, "mode": "card"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_tts_empty_validation(client: AsyncClient) -> None:
    res = await client.get("/api/tts?text=   ")
    assert res.status_code == 400
