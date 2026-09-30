"""Tests for the Headless Synthetic Learner Swarm (In-Process ASGI Fuzzing).

Validates multi-turn learner personas across the Deterministic Orchestrator and SQLite WAL persistence.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.dependencies import (
    get_grader_component,
    get_planning_worker,
    get_teaching_worker,
)
from apps.api.main import create_app
from goalcoach.infrastructure.config import Settings
from tests.fakes import FakeGraderComponent, FakePlanningWorker, FakeTeachingWorker
from tests.harness.synthetic_learner import SyntheticLearner


@pytest_asyncio.fixture
async def swarm_client(tmp_path: Path) -> AsyncClient:
    """Ephemeral in-process test client isolated from production/dev database."""
    db_file = tmp_path / f"swarm_test_{uuid4().hex[:8]}.db"
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{db_file}",
        content_database_url="sqlite:///./data/database1/goalcoach_hsk1_learning.db",
        log_file_path=str(tmp_path / "test_goalcoach.jsonl"),
    )
    application = create_app(settings)
    application.dependency_overrides[get_planning_worker] = FakePlanningWorker
    application.dependency_overrides[get_teaching_worker] = FakeTeachingWorker
    application.dependency_overrides[get_grader_component] = FakeGraderComponent

    async with application.router.lifespan_context(application):
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


@pytest.mark.asyncio
async def test_novice_persona(swarm_client: AsyncClient) -> None:
    """The Novice persona submits correct answers and advances progress smoothly."""
    learner = SyntheticLearner(swarm_client, persona_name="TheNovicePersona")

    # 1. Create Goal
    goal_res = await learner.create_goal(title="HSK 1 Novice Goal", target_hsk_level=1)
    assert goal_res["eventType"] == "GOAL_CREATED"
    assert goal_res["state"]["goal"]["title"] == "HSK 1 Novice Goal"

    # 2. Get Roadmap & Concepts
    concepts = await learner.get_curriculum_concepts(hsk_level=1)
    assert len(concepts) > 0
    first_concept = concepts[0]
    concept_id = first_concept["conceptId"]

    # 3. Start Session
    session_res = await learner.start_session(concept_id=concept_id)
    assert session_res["eventType"] == "SESSION_STARTED"
    assert session_res["state"]["activeSession"] is not None
    assert session_res.get("teachingAction") is not None
    assigned_exercise = session_res["teachingAction"]["exercisePayload"]
    assigned_id = assigned_exercise["exercise_id"]

    # 4. Fetch details to find accepted answer for assigned exercise
    details = await learner.get_concept_details(concept_id)
    exercises = details.get("exercises", [])
    matched_ex = next((e for e in exercises if e["id"] == assigned_id), None)
    accepted_answer = (
        matched_ex["acceptedAnswers"][0]
        if matched_ex and matched_ex.get("acceptedAnswers")
        else "Hello"
    )

    # 5. Submit correct answer
    ans_res = await learner.submit_answer(
        concept_id=concept_id,
        exercise_id=assigned_id,
        answer=accepted_answer,
    )
    assert ans_res["eventType"] == "ANSWER_SUBMITTED"
    assert ans_res["gradingResult"]["passedGates"] is True

    # 6. End session
    end_res = await learner.end_session()
    assert end_res["eventType"] == "SESSION_ENDED"
    assert end_res["state"]["activeSession"] is None


@pytest.mark.asyncio
async def test_struggling_persona(swarm_client: AsyncClient) -> None:
    """The Struggling persona submits erroneous answers, requests tutor help, and records mistakes."""
    learner = SyntheticLearner(swarm_client, persona_name="TheStrugglingPersona")

    await learner.create_goal(title="HSK 1 Remedial Track", daily_available_minutes=15)
    concepts = await learner.get_curriculum_concepts(hsk_level=1)
    concept_id = concepts[0]["conceptId"]

    session_res = await learner.start_session(concept_id=concept_id)
    assigned_id = session_res["teachingAction"]["exercisePayload"]["exercise_id"]

    # Deliberate wrong submission
    ans_res = await learner.submit_answer(
        concept_id=concept_id,
        exercise_id=assigned_id,
        answer="deliberately_wrong_submission_xyz",
    )
    assert ans_res["gradingResult"]["passedGates"] is False

    # Request tutor assistance
    help_res = await learner.request_help(
        concept_id=concept_id,
        current_exercise_id=assigned_id,
        query="Why is this answer incorrect?",
    )
    assert help_res["eventType"] == "HELP_REQUESTED"
    assert help_res["teachingAction"] is not None
    assert help_res["teachingAction"]["content"] != ""

    # Verify state error profile
    state = await learner.get_state()
    assert "errorProfile" in state["state"]
    errors = state["state"]["errorProfile"]
    assert any(e["conceptId"] == concept_id for e in errors)


@pytest.mark.asyncio
async def test_adversarial_persona_validation(swarm_client: AsyncClient) -> None:
    """The Adversarial persona verifies boundary validation and error containment."""
    learner = SyntheticLearner(swarm_client, persona_name="TheAdversarialPersona")

    await learner.create_goal(title="Adversarial Fuzzing", daily_available_minutes=30)
    concepts = await learner.get_curriculum_concepts(hsk_level=1)
    concept_id = concepts[0]["conceptId"]

    session_res = await learner.start_session(concept_id=concept_id)
    assigned_id = session_res["teachingAction"]["exercisePayload"]["exercise_id"]

    # 1. Blank whitespace answer rejected with 422
    import httpx

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await learner.submit_answer(
            concept_id=concept_id,
            exercise_id=assigned_id,
            answer="   ",
        )
    assert exc_info.value.response.status_code == 422

    # 2. Unknown exercise ID rejected with 422
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await learner.submit_answer(
            concept_id=concept_id,
            exercise_id="non_existent_exercise_12345",
            answer="Valid text",
        )
    assert exc_info.value.response.status_code == 422

    # 3. Large string (1000 chars) accepted without 500 error
    long_answer = "测试" * 500
    res = await learner.submit_answer(
        concept_id=concept_id,
        exercise_id=assigned_id,
        answer=long_answer,
    )
    assert res["eventType"] == "ANSWER_SUBMITTED"


@pytest.mark.asyncio
async def test_concurrent_multi_persona_swarm(swarm_client: AsyncClient) -> None:
    """Launch 4 concurrent learner personas simultaneously to stress the orchestrator and WAL locks."""

    async def run_learner_journey(persona_name: str, index: int) -> None:
        learner = SyntheticLearner(
            swarm_client,
            learner_id=f"swarm_user_{index}_{uuid4().hex[:6]}",
            persona_name=persona_name,
        )
        await learner.create_goal(
            title=f"Goal for {persona_name} {index}", daily_available_minutes=20
        )
        session_res = await learner.start_session()
        if session_res.get("teachingAction") and session_res["teachingAction"].get(
            "exercisePayload"
        ):
            assigned_exercise = session_res["teachingAction"]["exercisePayload"]
            target_concept_id = assigned_exercise["concept_id"]
            assigned_id = assigned_exercise["exercise_id"]
            details = await learner.get_concept_details(target_concept_id)
            exercises = details.get("exercises", [])
            matched_ex = next((e for e in exercises if e["id"] == assigned_id), None)
            answer = (
                matched_ex["acceptedAnswers"][0]
                if matched_ex and matched_ex.get("acceptedAnswers")
                else "Hello"
            )
            await learner.submit_answer(
                concept_id=target_concept_id, exercise_id=assigned_id, answer=answer
            )
        await learner.end_session()

    # Run 4 personas concurrently
    tasks = [
        run_learner_journey("NovicePacer", 0),
        run_learner_journey("StrugglingReviewer", 1),
        run_learner_journey("CuriousExplorer", 2),
        run_learner_journey("IntensiveDriller", 3),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        assert not isinstance(res, Exception), f"Concurrent swarm failure: {res}"
