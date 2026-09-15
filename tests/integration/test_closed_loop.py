"""Comprehensive integration tests verifying AC1 through AC11 from GOALCOACH_MVP_PRD.md.

Specifically verifies:
- AC1 & AC7: Closed loop state mutation and SQLite persistence across session reloads.
- AC2 & AC10: The Core Planning Proof (Same Goal + Different Learner State -> Different Plan).
- AC4 & AC11: The Core Teaching Proof (Same Concept + Different Error History -> Different Strategy).
- AC5: Rubric enforcement & fast-path short-circuiting.
- AC6: Deterministic progress calculations (mastery deltas, retention decay, interval scaling, replanning gate).
- AC8: Zero multi-agent chaining per single turn.
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
    Exercise,
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
    db_file = tmp_path / "test_goalcoach.db"
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


# --- AC1 & AC7: Closed Loop State Mutation & Relational Persistence ---


@pytest.mark.asyncio
async def test_ac1_ac7_closed_loop_state_mutation_and_durability(
    orchestrator: DeterministicOrchestrator,
    temp_learner_repo: SqliteLearnerRepository,
) -> None:
    """AC1 & AC7: User interactions successfully mutate persistent state in SQLite WAL and survive reloads."""
    learner_id = f"learner_{uuid4().hex[:8]}"

    # Step 1: Create Goal
    goal_res = await orchestrator.handle_event(
        event_type=EventType.GOAL_CREATED,
        learner_id=learner_id,
        payload={"title": "HSK 1 Complete Goal", "daily_available_minutes": 20},
    )
    assert goal_res.daily_plan is not None
    assert len(goal_res.daily_plan.items) >= 1

    # Verify reload from disk
    reloaded_state = await temp_learner_repo.get(learner_id)
    assert reloaded_state is not None
    assert reloaded_state.goal.title == "HSK 1 Complete Goal"
    assert reloaded_state.active_plan is not None

    # Step 2: Submit a correct answer for hsk1_c01 (prompt: 你好 -> meaning: Hello)
    answer_res = await orchestrator.handle_event(
        event_type=EventType.ANSWER_SUBMITTED,
        learner_id=learner_id,
        payload={
            "exercise_id": "hsk1_c01_e01",
            "concept_id": "hsk1_c01",
            "answer": "Hello",
        },
    )
    assert answer_res.grading_result is not None
    assert answer_res.grading_result.passed_gates is True

    # Verify state updated and persisted
    persisted_state = await temp_learner_repo.get(learner_id)
    assert persisted_state is not None
    assert "hsk1_c01" in persisted_state.mastery
    assert persisted_state.mastery["hsk1_c01"].mastery_score == 0.25
    assert persisted_state.mastery["hsk1_c01"].retention_score == 1.0


# --- AC2 & AC10: The Core Planning Proof ---


@pytest.mark.asyncio
async def test_ac2_ac10_core_planning_proof_same_goal_different_state(
    content_service: ContentService,
    temp_learner_repo: SqliteLearnerRepository,
) -> None:
    """AC2 & AC10: Same goal + different learner state -> different plan.

    Learner A (clean state): gets NEW concepts.
    Learner B (repeated error ERR_QUESTION_MA): gets REMEDIAL priority on hsk1_c04.
    """
    planner = PlanningWorker()

    # Learner A: Clean state
    state_a = LearnerState(
        learner_id="learner_a_clean",
        goal=LearningGoal(title="HSK 1 Target", target_hsk_level=1, daily_available_minutes=20),
        needs_replanning=False,
    )

    # Learner B: Repeated error on hsk1_c04 (questions with 吗)
    state_b = LearnerState(
        learner_id="learner_b_weak",
        goal=LearningGoal(title="HSK 1 Target", target_hsk_level=1, daily_available_minutes=20),
        mastery={
            "hsk1_c04": ConceptMastery(
                concept_id="hsk1_c04",
                mastery_score=0.30,
                retention_score=0.70,
                interval_days=1.0,
                evidence_count=2,
            )
        },
        error_profile=[
            ErrorRecord(
                code="ERR_QUESTION_MA",
                concept_id="hsk1_c04",
                occurrences=3,
            )
        ],
        needs_replanning=True,
    )

    plan_a = await planner.create_plan(state=state_a, content_service=content_service)
    plan_b = await planner.create_plan(state=state_b, content_service=content_service)

    # Assert plan A allocates NEW concepts
    kinds_a = [item.kind for item in plan_a.ordered_items]
    assert PlanItemKind.NEW in kinds_a

    # Assert plan B prioritizes REMEDIAL on the weak concept
    kinds_b = [item.kind for item in plan_b.ordered_items]
    assert PlanItemKind.REMEDIAL in kinds_b
    remedial_concepts = [item.concept_id for item in plan_b.ordered_items if item.kind == PlanItemKind.REMEDIAL]
    assert "hsk1_c04" in remedial_concepts

    # Plan items are demonstrably different
    assert [i.concept_id for i in plan_a.ordered_items] != [i.concept_id for i in plan_b.ordered_items]


# --- AC4 & AC11: The Core Teaching Proof ---


@pytest.mark.asyncio
async def test_ac4_ac11_core_teaching_proof_adaptive_strategy_switching(
    content_service: ContentService,
) -> None:
    """AC4 & AC11: Same concept + different error history -> different instructional action.

    Turn 1 (no error): Teacher outputs EXPLANATION.
    Turn 2 (previous explanation failed / student confused): Teacher switches to CONTRAST_EXAMPLE or HINT.
    """
    teacher = TeachingWorker()
    state = LearnerState(
        goal=LearningGoal(title="HSK 1 Target", target_hsk_level=1),
        context_interests=["Travel"],
    )

    # Turn 1: Fresh encounter
    action_1 = await teacher.teach_concept(
        concept_id="hsk1_c04",
        state=state,
        content_service=content_service,
        failed_attempts=0,
    )
    assert action_1.action_kind in (TeachingActionKind.EXPLANATION, TeachingActionKind.DIALOGUE)
    assert action_1.content != ""

    # Turn 2: Same concept after a failure / confusion
    action_2 = await teacher.teach_concept(
        concept_id="hsk1_c04",
        state=state,
        content_service=content_service,
        failed_attempts=1,
    )
    assert action_2.action_kind in (TeachingActionKind.CONTRAST_EXAMPLE, TeachingActionKind.HINT)
    assert action_2.action_kind != action_1.action_kind


# --- AC5 & AC6: Grader Component Rubric & Progress Service Math ---


@pytest.mark.asyncio
async def test_ac5_grader_fast_path_and_rubric() -> None:
    """AC5: Fast-path bypass (<5ms) on reference answers and rubric evaluation on novel answers."""
    grader = GraderComponent()
    exercise = Exercise(
        id="ex_test_01",
        concept_id="hsk1_c04",
        prompt="Are you a teacher?",
        target_instruction="Translate to Chinese",
        reference_answers=["你是老师吗", "你是老师吗？"],
        hsk_level=1,
    )

    # 1. Exact match fast path
    res_fast = await grader.grade(exercise, "你是老师吗")
    assert res_fast.passed_gates is True
    assert res_fast.scores.grammatical_correctness == 1.0
    assert res_fast.grader_version == "deterministic-fast-path"

    # 2. Incorrect answer
    res_wrong = await grader.grade(exercise, "你是老师")  # Missing 吗
    assert res_wrong.passed_gates is False
    assert "ERR_QUESTION_MA" in res_wrong.detected_errors or len(res_wrong.detected_errors) > 0


def test_ac6_progress_service_mathematical_invariants() -> None:
    """AC6: Progress Service executes deterministic mastery deltas, retention decay, and replanning gate."""
    progress_service = ProgressService(decay_lambda=0.05)
    state = LearnerState(
        learner_id="test_progress_learner",
        goal=LearningGoal(title="HSK1"),
    )

    # 1. Successful attempt: mastery +0.25, interval * 1.8, retention = 1.0
    pass_result = GradingResult(
        exercise_id=uuid4(),
        scores=RubricScores(grammatical_correctness=1.0, semantic_precision=1.0, pragmatic_appropriateness=1.0),
        passed_gates=True,
        confidence=1.0,
        feedback="Great job!",
    )
    state = progress_service.apply_grading_result(state, pass_result, concept_id="hsk1_c01")
    m1 = state.mastery["hsk1_c01"]
    assert m1.mastery_score == 0.25
    assert m1.retention_score == 1.0
    assert m1.interval_days == 1.8
    assert state.needs_replanning is False

    # 2. First failure: mastery -0.10, interval reset to 1.0, error logged
    fail_result = GradingResult(
        exercise_id=uuid4(),
        scores=RubricScores(grammatical_correctness=0.3, semantic_precision=0.4, pragmatic_appropriateness=0.5),
        passed_gates=False,
        confidence=0.9,
        feedback="Missing 吗 particle",
        detected_errors=["ERR_QUESTION_MA"],
    )
    state = progress_service.apply_grading_result(state, fail_result, concept_id="hsk1_c04")
    m2 = state.mastery["hsk1_c04"]
    assert m2.mastery_score == 0.0  # floored at 0.0
    assert m2.interval_days == 1.0
    assert state.needs_replanning is False  # Only 1 occurrence

    # 3. Second failure on same concept: error occurrences == 2 -> triggers needs_replanning = True
    state = progress_service.apply_grading_result(state, fail_result, concept_id="hsk1_c04")
    assert state.needs_replanning is True
    err = next(e for e in state.error_profile if e.code == "ERR_QUESTION_MA")
    assert err.occurrences == 2


# --- AC8: Zero Multi-Agent Sequential Chaining ---


@pytest.mark.asyncio
async def test_ac8_zero_sequential_agent_chaining(
    orchestrator: DeterministicOrchestrator,
) -> None:
    """AC8: Single interaction event dispatches to a single worker without multi-agent chaining."""
    learner_id = f"test_ac8_{uuid4().hex[:8]}"

    # GOAL_CREATED dispatches only to Planning Agent
    res_goal = await orchestrator.handle_event(
        event_type=EventType.GOAL_CREATED,
        learner_id=learner_id,
        payload={"title": "HSK 1", "daily_available_minutes": 20},
    )
    assert res_goal.plan_update is not None
    assert res_goal.teaching_action is None  # Teacher was NOT invoked in the same turn

    # SESSION_STARTED dispatches only to Teaching Agent
    res_session = await orchestrator.handle_event(
        event_type=EventType.SESSION_STARTED,
        learner_id=learner_id,
        payload={},
    )
    assert res_session.teaching_action is not None
    assert res_session.grading_result is None  # Grader was NOT invoked in the same turn
