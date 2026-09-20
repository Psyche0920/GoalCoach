"""Integration test suite verifying the hardened remediation engine and edge cases.

Specifically stress-tests and validates:
1. Remediation triggers on repeated failures (occurrences >= 2) with needs_replanning = True.
2. Dynamic exercise rotation (rotates from failed e01 to unattempted e02).
3. Error profile resolution & decay on passing gating rubrics (needs_replanning = False).
4. Prerequisite DAG progression (advances to hsk1_c02 without stepping gap trap).
5. Multi-error collision resolution on same concept.
6. Exercise exhaustion graceful fallback (no IndexError).
7. Zero error profile ingress on remedial item (modality adapts to CONTRAST_EXAMPLE).
8. Strict DAG prerequisite blocking and remediated-unlocking.
9. SQLite WAL round-trip persistence of new state fields.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from goalcoach.agents.grader_component import GraderComponent
from goalcoach.agents.planning_agent import PlanningWorker
from goalcoach.agents.teaching_agent import TeachingWorker
from goalcoach.application.orchestrator import DeterministicOrchestrator
from goalcoach.application.progress_service import ProgressService
from goalcoach.domain.enums import EventType, PlanItemKind, TeachingActionKind
from goalcoach.domain.models import (
    ConceptMastery,
    ErrorRecord,
    GradingResult,
    LearnerState,
    LearningGoal,
    RubricScores,
)
from goalcoach.infrastructure.persistence.content_service import ContentService
from goalcoach.infrastructure.persistence.database import (
    create_learner_schema,
    create_session_factory,
)
from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    SqliteLearnerRepository,
)

CONTENT_DB_PATH = Path("data/database1/goalcoach_hsk1_learning.db")


@pytest.fixture
def content_service() -> ContentService:
    if not CONTENT_DB_PATH.exists():
        pytest.skip(f"Curriculum DB missing at {CONTENT_DB_PATH}")
    factory = create_session_factory(f"sqlite:///{CONTENT_DB_PATH}")
    repo = ContentRepository(factory)
    return ContentService(repo)


@pytest.fixture
def temp_learner_repo(tmp_path: Path) -> SqliteLearnerRepository:
    db_file = tmp_path / "test_goalcoach_remediation.db"
    factory = create_session_factory(f"sqlite:///{db_file}")
    create_learner_schema(factory)
    return SqliteLearnerRepository(factory)


@pytest.fixture
def orchestrator(
    temp_learner_repo: SqliteLearnerRepository,
    content_service: ContentService,
) -> DeterministicOrchestrator:
    progress_service = ProgressService(learner_repo=temp_learner_repo)
    planning_worker = PlanningWorker()
    teaching_worker = TeachingWorker()
    grader_worker = GraderComponent()

    return DeterministicOrchestrator(
        learner_repo=temp_learner_repo,
        content_service=content_service,
        progress_service=progress_service,
        planning_worker=planning_worker,
        teaching_worker=teaching_worker,
        grader_worker=grader_worker,
    )


# --- 1. Remediation Triggering & Replanning ---


@pytest.mark.asyncio
async def test_remediation_triggers_after_repeated_errors(
    orchestrator: DeterministicOrchestrator,
    temp_learner_repo: SqliteLearnerRepository,
) -> None:
    """Submitting 2 consecutive incorrect answers on hsk1_c01 triggers replanning with a REMEDIAL item."""
    learner_id = f"learner_trigger_{uuid4().hex[:8]}"

    # Step 1: Initialize goal
    await orchestrator.handle_event(
        event_type=EventType.GOAL_CREATED,
        learner_id=learner_id,
        payload={"title": "HSK 1", "daily_available_minutes": 20},
    )

    # Step 2: Fail attempt 1 (occurrences = 1)
    res_1 = await orchestrator.handle_event(
        event_type=EventType.ANSWER_SUBMITTED,
        learner_id=learner_id,
        payload={"exercise_id": "hsk1_c01_e01", "concept_id": "hsk1_c01", "answer": "Wrong1"},
    )
    assert res_1.grading_result.passed_gates is False
    assert res_1.replanned is False

    # Step 3: Fail attempt 2 (occurrences = 2 -> triggers replanning)
    res_2 = await orchestrator.handle_event(
        event_type=EventType.ANSWER_SUBMITTED,
        learner_id=learner_id,
        payload={"exercise_id": "hsk1_c01_e01", "concept_id": "hsk1_c01", "answer": "Wrong2"},
    )
    assert res_2.grading_result.passed_gates is False
    assert res_2.replanned is True
    assert res_2.daily_plan is not None
    assert res_2.daily_plan.items[0].kind == PlanItemKind.REMEDIAL
    assert res_2.daily_plan.items[0].concept_id == "hsk1_c01"

    # Verify state in DB
    state = await temp_learner_repo.get(learner_id)
    assert state is not None
    assert state.needs_replanning is False  # Reset by orchestrator after creating adapted plan
    assert "hsk1_c01_e01" in state.today_mistake_exercise_ids


# --- 2. Dynamic Exercise Rotation ---


@pytest.mark.asyncio
async def test_remediation_exercise_rotates_and_does_not_repeat_e01(
    orchestrator: DeterministicOrchestrator,
) -> None:
    """When in remediation for hsk1_c01, the system must serve hsk1_c01_e02, avoiding stagnation on e01."""
    learner_id = f"learner_rotate_{uuid4().hex[:8]}"

    # Initialize goal and trigger failures
    await orchestrator.handle_event(
        event_type=EventType.GOAL_CREATED,
        learner_id=learner_id,
        payload={"title": "HSK 1", "daily_available_minutes": 20},
    )

    # Fail 2 times on e01
    for i in range(2):
        await orchestrator.handle_event(
            event_type=EventType.ANSWER_SUBMITTED,
            learner_id=learner_id,
            payload={
                "exercise_id": "hsk1_c01_e01",
                "concept_id": "hsk1_c01",
                "answer": f"Mistake_{i}",
            },
        )

    # Start remedial session
    session_res = await orchestrator.handle_event(
        event_type=EventType.SESSION_STARTED,
        learner_id=learner_id,
        payload={},
    )

    action = session_res.teaching_action
    assert action is not None
    # Exercise must NOT be e01
    assert action.exercise_payload is not None
    assert action.exercise_payload["exercise_id"] == "hsk1_c01_e02"
    assert action.exercise_payload["prompt"] == "Goodbye"

    # Modality must adapt away from EXPLANATION because failed_attempts >= 1
    assert action.action_kind in (
        TeachingActionKind.CONTRAST_EXAMPLE,
        TeachingActionKind.HINT,
        TeachingActionKind.RETRY,
    )


# --- 3. Error Profile Resolution & Decay ---


@pytest.mark.asyncio
async def test_remediation_success_clears_error_profile_and_resets_replanning(
    orchestrator: DeterministicOrchestrator,
    temp_learner_repo: SqliteLearnerRepository,
) -> None:
    """Passing a remedial exercise resolves the concept's errors and marks it remediated today."""
    learner_id = f"learner_clear_{uuid4().hex[:8]}"

    await orchestrator.handle_event(
        event_type=EventType.GOAL_CREATED,
        learner_id=learner_id,
        payload={"title": "HSK 1", "daily_available_minutes": 20},
    )

    # Fail twice to slot remediation
    for i in range(2):
        await orchestrator.handle_event(
            event_type=EventType.ANSWER_SUBMITTED,
            learner_id=learner_id,
            payload={"exercise_id": "hsk1_c01_e01", "concept_id": "hsk1_c01", "answer": "Wrong"},
        )

    # Start session to receive e02
    await orchestrator.handle_event(
        event_type=EventType.SESSION_STARTED,
        learner_id=learner_id,
        payload={},
    )

    # Submit correct answer for e02 ("再见")
    pass_res = await orchestrator.handle_event(
        event_type=EventType.ANSWER_SUBMITTED,
        learner_id=learner_id,
        payload={"exercise_id": "hsk1_c01_e02", "concept_id": "hsk1_c01", "answer": "再见"},
    )
    assert pass_res.grading_result.passed_gates is True
    assert pass_res.replanned is False  # Must not trigger immediate turn-level replanning

    # Verify state in repository
    state = await temp_learner_repo.get(learner_id)
    assert state is not None
    assert len(state.error_profile) == 0  # Errors for hsk1_c01 resolved!
    assert "hsk1_c01" in state.today_remediated_concept_ids
    assert "hsk1_c01_e02" in state.today_completed_exercise_ids
    assert state.needs_replanning is False


# --- 4. Curriculum Progression Without Stepping Gap Trap ---


@pytest.mark.asyncio
async def test_curriculum_advances_after_remediation_without_infinite_loop(
    orchestrator: DeterministicOrchestrator,
    temp_learner_repo: SqliteLearnerRepository,
) -> None:
    """After passing remediation for hsk1_c01, the system seamlessly advances to hsk1_c02."""
    learner_id = f"learner_advance_{uuid4().hex[:8]}"

    await orchestrator.handle_event(
        event_type=EventType.GOAL_CREATED,
        learner_id=learner_id,
        payload={"title": "HSK 1", "daily_available_minutes": 20},
    )

    # Fail twice on e01
    for _ in range(2):
        await orchestrator.handle_event(
            event_type=EventType.ANSWER_SUBMITTED,
            learner_id=learner_id,
            payload={"exercise_id": "hsk1_c01_e01", "concept_id": "hsk1_c01", "answer": "Wrong"},
        )

    # Session start (gets e02)
    await orchestrator.handle_event(
        event_type=EventType.SESSION_STARTED,
        learner_id=learner_id,
        payload={},
    )

    # Pass remedial exercise e02
    await orchestrator.handle_event(
        event_type=EventType.ANSWER_SUBMITTED,
        learner_id=learner_id,
        payload={"exercise_id": "hsk1_c01_e02", "concept_id": "hsk1_c01", "answer": "再见"},
    )

    # Next session turn: previous remedial plan item was completed, plan should regenerate
    next_session = await orchestrator.handle_event(
        event_type=EventType.SESSION_STARTED,
        learner_id=learner_id,
        payload={},
    )

    # Verify the curriculum has moved forward to hsk1_c02
    assert next_session.teaching_action is not None
    assert next_session.teaching_action.concept_id == "hsk1_c02"
    assert next_session.teaching_action.exercise_payload["exercise_id"] == "hsk1_c02_e01"
    # Fresh encounter for hsk1_c02 should be EXPLANATION or DIALOGUE
    assert next_session.teaching_action.action_kind in (
        TeachingActionKind.EXPLANATION,
        TeachingActionKind.DIALOGUE,
    )


# --- 5. Stress Test: Multiple Distinct Errors for Same Concept ---


@pytest.mark.asyncio
async def test_edge_case_multiple_distinct_errors_for_same_concept(
    temp_learner_repo: SqliteLearnerRepository,
) -> None:
    """Learner has accumulated multiple distinct error tags for hsk1_c01; passing remediation resolves both."""
    progress_service = ProgressService(learner_repo=temp_learner_repo)

    state = LearnerState(
        learner_id="multi_error_learner",
        goal=LearningGoal(title="HSK1"),
        error_profile=[
            ErrorRecord(code="ERR_VOCAB_MEANING", concept_id="hsk1_c01", occurrences=2),
            ErrorRecord(code="ERR_QUESTION_MA", concept_id="hsk1_c01", occurrences=3),
        ],
        needs_replanning=True,
    )
    # Give active plan with remedial item
    from goalcoach.domain.models import DailyPlan, PlanItem

    state.active_plan = DailyPlan(
        learner_id=state.learner_id,
        items=[
            PlanItem(
                concept_id="hsk1_c01",
                kind=PlanItemKind.REMEDIAL,
                objective="Remediate hsk1_c01",
                estimated_minutes=10,
            )
        ],
        rationale="Remedial plan",
    )

    pass_result = GradingResult(
        exercise_id="hsk1_c01_e02",
        scores=RubricScores(
            grammatical_correctness=1.0, semantic_precision=1.0, pragmatic_appropriateness=1.0
        ),
        passed_gates=True,
        confidence=1.0,
        feedback="Perfect!",
    )

    updated_state = progress_service.apply_grading_result(state, pass_result, concept_id="hsk1_c01")

    # All errors for hsk1_c01 should be cleared
    assert len(updated_state.error_profile) == 0
    assert updated_state.needs_replanning is False
    assert "hsk1_c01" in updated_state.today_remediated_concept_ids
    assert "hsk1_c01_e02" in updated_state.today_completed_exercise_ids


# --- 6. Stress Test: Exercise Exhaustion Graceful Fallback ---


@pytest.mark.asyncio
async def test_edge_case_exercise_exhaustion_graceful_fallback(
    content_service: ContentService,
) -> None:
    """When all exercises for a concept have been attempted, system does not crash and safely falls back."""
    all_exercises = content_service.get_exercises_for_concept("hsk1_c01", limit=100)
    all_exercise_ids = [e.exercise_id for e in all_exercises]
    teacher = TeachingWorker()
    state = LearnerState(
        goal=LearningGoal(title="HSK1"),
        today_completed_exercise_ids=all_exercise_ids,
    )

    # Should not raise IndexError
    action = await teacher.teach_concept(
        concept_id="hsk1_c01",
        state=state,
        content_service=content_service,
        failed_attempts=0,
    )
    assert action.exercise_payload is not None
    assert action.exercise_payload["exercise_id"] in all_exercise_ids


# --- 7. Stress Test: Zero Error Profile Ingress on Remedial Item ---


@pytest.mark.asyncio
async def test_edge_case_zero_error_profile_remedial_ingress(
    orchestrator: DeterministicOrchestrator,
) -> None:
    """A REMEDIAL plan item with empty error_profile defaults failed_attempts=1 to trigger adaptive modality."""
    learner_id = f"learner_zero_err_{uuid4().hex[:8]}"

    # Manually configure state with REMEDIAL item but empty error_profile
    from goalcoach.domain.models import DailyPlan, PlanItem

    state = LearnerState(
        learner_id=learner_id,
        goal=LearningGoal(title="HSK 1"),
        error_profile=[],
        active_plan=DailyPlan(
            learner_id=learner_id,
            items=[
                PlanItem(
                    concept_id="hsk1_c01",
                    kind=PlanItemKind.REMEDIAL,
                    objective="Manual remedial allocation",
                    estimated_minutes=10,
                )
            ],
            rationale="Manually triggered remediation",
        ),
    )
    await orchestrator.learner_repo.save(state)

    session_res = await orchestrator.handle_event(
        event_type=EventType.SESSION_STARTED,
        learner_id=learner_id,
        payload={},
    )
    action = session_res.teaching_action
    # Modality must adapt away from fresh EXPLANATION because it is a REMEDIAL item
    assert action.action_kind in (
        TeachingActionKind.CONTRAST_EXAMPLE,
        TeachingActionKind.HINT,
        TeachingActionKind.RETRY,
    )


# --- 8. Stress Test: Prerequisite DAG Strict Blocking and Remediated Unlocking ---


@pytest.mark.asyncio
async def test_edge_case_prerequisite_dag_blocks_unready_and_unlocks_remediated(
    content_service: ContentService,
) -> None:
    """hsk1_c02 requires hsk1_c01. It is strictly blocked if hsk1_c01 has 0 mastery, but unlocked if remediated."""
    planner = PlanningWorker()

    # Case A: Clean state -> hsk1_c02 is blocked because hsk1_c01 not started
    state_a = LearnerState(goal=LearningGoal(title="HSK1", daily_available_minutes=20))
    plan_a = await planner.create_plan(state=state_a, content_service=content_service)
    assert plan_a.ordered_items[0].concept_id == "hsk1_c01"
    assert all(it.concept_id != "hsk1_c02" for it in plan_a.ordered_items)

    # Case B: hsk1_c01 was remediated today with mastery 0.25 -> hsk1_c02 is UNLOCKED
    state_b = LearnerState(
        goal=LearningGoal(title="HSK1", daily_available_minutes=20),
        mastery={
            "hsk1_c01": ConceptMastery(concept_id="hsk1_c01", mastery_score=0.25, evidence_count=1)
        },
        today_remediated_concept_ids=["hsk1_c01"],
        today_studied_concept_ids=["hsk1_c01"],
    )
    plan_b = await planner.create_plan(state=state_b, content_service=content_service)
    # The first item must be hsk1_c02 (NEW)
    assert plan_b.ordered_items[0].concept_id == "hsk1_c02"
    assert plan_b.ordered_items[0].kind == PlanItemKind.NEW
    # hsk1_c03 requires hsk1_c02, so hsk1_c03 must still be blocked!
    assert all(it.concept_id != "hsk1_c03" for it in plan_b.ordered_items)


# --- 9. Stress Test: SQLite WAL Persistence Round-Trip of New State Fields ---


@pytest.mark.asyncio
async def test_edge_case_state_persistence_and_reload_with_new_fields(
    temp_learner_repo: SqliteLearnerRepository,
) -> None:
    """State with today_completed_exercise_ids and today_remediated_concept_ids survives SQLite WAL roundtrips."""
    learner_id = f"wal_test_{uuid4().hex[:8]}"
    state = LearnerState(
        learner_id=learner_id,
        goal=LearningGoal(title="HSK1"),
        today_completed_exercise_ids=["hsk1_c01_e01", "hsk1_c01_e02"],
        today_mistake_exercise_ids=["hsk1_c01_e01"],
        today_remediated_concept_ids=["hsk1_c01"],
    )

    # Save to disk
    await temp_learner_repo.save(state)

    # Reload from disk
    reloaded = await temp_learner_repo.get(learner_id)
    assert reloaded is not None
    assert reloaded.today_completed_exercise_ids == ["hsk1_c01_e01", "hsk1_c01_e02"]
    assert reloaded.today_remediated_concept_ids == ["hsk1_c01"]
    assert reloaded.all_attempted_exercise_ids() == {"hsk1_c01_e01", "hsk1_c01_e02"}
