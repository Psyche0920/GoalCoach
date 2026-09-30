"""Exercise failed replanning, stale exercise rejection, and session recovery."""

import pytest
from httpx import AsyncClient

from goalcoach.infrastructure.llm.pydantic_ai_models import AgentOutputError
from goalcoach.infrastructure.persistence.repositories import (
    SqlAlchemyLearnerRepository,
    StaleLearnerStateError,
)
from tests.fakes import FakePlanningWorker


@pytest.mark.asyncio
async def test_state_conflict_has_a_distinct_recovery_code(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def stale(*args: object, **kwargs: object) -> None:
        raise StaleLearnerStateError("A concurrent request saved a newer version")

    monkeypatch.setattr(SqlAlchemyLearnerRepository, "save", stale)
    response = await client.post(
        "/api/v1/events",
        json={
            "event_type": "SESSION_STARTED",
            "learner_id": "conflict-test",
            "payload": {},
        },
    )
    assert response.status_code == 409
    assert response.headers["x-goalcoach-error"] == "STATE_CONFLICT"


@pytest.mark.asyncio
async def test_failed_replan_can_resume_without_resubmitting_old_answer(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    learner_id = "replan-recovery"
    response = await client.post(
        "/api/v1/events",
        json={
            "event_type": "GOAL_CREATED",
            "learner_id": learner_id,
            "payload": {"title": "Greetings", "daily_available_minutes": 20},
        },
    )
    assert response.status_code == 200
    for _ in range(2):
        response = await client.post(
            "/api/v1/events",
            json={
                "event_type": "SESSION_STARTED",
                "learner_id": learner_id,
                "payload": {},
            },
        )
        assert response.status_code == 200
        action = response.json()["teachingAction"]
        answer = {
            "exercise_id": action["exercisePayload"]["exercise_id"],
            "concept_id": action["conceptId"],
            "answer": "incorrect test answer",
        }
        response = await client.post(
            "/api/v1/events",
            json={
                "event_type": "ANSWER_SUBMITTED",
                "learner_id": learner_id,
                "payload": answer,
            },
        )
        assert response.status_code == 200
    assert response.json()["nextAction"] == "plan"
    response = await client.post(
        "/api/v1/events",
        json={
            "event_type": "SESSION_ENDED",
            "learner_id": learner_id,
            "payload": {},
        },
    )
    assert response.status_code == 200

    async def fail(*args: object, **kwargs: object) -> None:
        raise AgentOutputError("Planning Agent did not prioritize the required remediation item.")

    with monkeypatch.context() as patch:
        patch.setattr(FakePlanningWorker, "create_plan", fail)
        response = await client.post(
            "/api/v1/events",
            json={
                "event_type": "SESSION_STARTED",
                "learner_id": learner_id,
                "payload": {},
            },
        )
    assert response.status_code == 502
    assert "required remediation" in response.json()["detail"]
    response = await client.post(
        "/api/v1/events",
        json={
            "event_type": "ANSWER_SUBMITTED",
            "learner_id": learner_id,
            "payload": answer,
        },
    )
    assert response.status_code == 409
    assert response.headers["x-goalcoach-error"] == "SESSION_INVALID"
    refreshed = await client.get(f"/api/v1/learners/{learner_id}")
    assert refreshed.json()["nextAction"] == "plan"
    assert refreshed.json()["state"]["activeSession"] is None

    # Retry planning, then request a fresh teaching turn before accepting answers.
    for _ in range(2):
        response = await client.post(
            "/api/v1/events",
            json={
                "event_type": "SESSION_STARTED",
                "learner_id": learner_id,
                "payload": {},
            },
        )
        assert response.status_code == 200
    action = response.json()["teachingAction"]
    response = await client.post(
        "/api/v1/events",
        json={
            "event_type": "ANSWER_SUBMITTED",
            "learner_id": learner_id,
            "payload": {
                "exercise_id": action["exercisePayload"]["exercise_id"],
                "concept_id": action["conceptId"],
                "answer": "incorrect test answer",
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["gradingResult"] is not None
