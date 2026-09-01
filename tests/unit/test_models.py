from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import pytest
from pydantic import ValidationError

from goalcoach.domain.enums import PlanItemKind, PlanStatus, RetrievalMode
from goalcoach.domain.models import (
    AnswerSubmission,
    ConceptDelta,
    ConceptMastery,
    DailyPlan,
    ErrorRecord,
    Exercise,
    GradingResult,
    LearnerState,
    LearningGoal,
    PlanItem,
    ProgressUpdate,
    RetrievalRequest,
    RubricScores,
    SessionSummary,
    utc_now,
)


# --- Score & Boundary Clamping Tests ---


def test_score_boundary_clamping() -> None:
    # RubricScores uses Score (ge=0.0, le=1.0)
    valid_scores = RubricScores(
        grammatical_correctness=0.0,
        semantic_precision=1.0,
        pragmatic_appropriateness=0.5,
    )
    assert valid_scores.grammatical_correctness == 0.0
    assert valid_scores.semantic_precision == 1.0

    with pytest.raises(ValidationError):
        RubricScores(
            grammatical_correctness=-0.01,
            semantic_precision=0.5,
            pragmatic_appropriateness=0.5,
        )

    with pytest.raises(ValidationError):
        RubricScores(
            grammatical_correctness=0.5,
            semantic_precision=1.01,
            pragmatic_appropriateness=0.5,
        )


def test_learning_goal_validation() -> None:
    goal = LearningGoal(
        title="Master HSK 3",
        target_hsk_level=3,
        daily_available_minutes=30,
    )
    assert isinstance(goal.id, UUID)
    assert goal.target_hsk_level == 3
    assert goal.daily_available_minutes == 30
    assert goal.version == 1

    # Empty title rejected
    with pytest.raises(ValidationError):
        LearningGoal(title="")

    # Invalid HSK level (< 1 or > 6)
    with pytest.raises(ValidationError):
        LearningGoal(title="HSK 0", target_hsk_level=0)
    with pytest.raises(ValidationError):
        LearningGoal(title="HSK 7", target_hsk_level=7)

    # Invalid daily minutes (<= 0 or > 240)
    with pytest.raises(ValidationError):
        LearningGoal(title="HSK 3", daily_available_minutes=0)
    with pytest.raises(ValidationError):
        LearningGoal(title="HSK 3", daily_available_minutes=241)


# --- ConceptMastery & Spaced Repetition Tests ---


def test_concept_mastery_retention_and_due_check() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    cm = ConceptMastery(
        concept_id="grammar_le_completed",
        mastery_score=0.8,
        retention_score=1.0,
        decay_lambda=0.05,
        last_reviewed_at=now,
        next_review_at=now + timedelta(days=3),
    )

    # No decay immediately at review time
    assert cm.current_retention(at=now) == pytest.approx(1.0)

    # Decayed retention after 5 days
    decayed = cm.current_retention(at=now + timedelta(days=5))
    assert decayed < 1.0
    assert decayed > 0.0

    # Review due check
    assert not cm.is_review_due(at=now + timedelta(days=2))
    assert cm.is_review_due(at=now + timedelta(days=3))
    assert cm.is_review_due(at=now + timedelta(days=4))

    # None next_review_at should never be due
    cm_no_due = ConceptMastery(concept_id="vocab_pingguo", next_review_at=None)
    assert not cm_no_due.is_review_due()


def test_concept_mastery_is_review_due_timezone_mismatch() -> None:
    # Test naive next_review_at with aware current_time and vice-versa
    naive_dt = datetime(2026, 9, 1, 12, 0, 0)
    aware_future = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    aware_past = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)

    cm = ConceptMastery(concept_id="c1", next_review_at=naive_dt)
    assert cm.is_review_due(at=aware_future)
    assert not cm.is_review_due(at=aware_past)

    cm_aware = ConceptMastery(
        concept_id="c2",
        next_review_at=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert cm_aware.is_review_due(at=datetime(2026, 9, 2, 12, 0, 0))
    assert not cm_aware.is_review_due(at=datetime(2026, 8, 31, 12, 0, 0))


# --- Weighted Progress Calculations ---


def test_learner_state_overall_progress_empty() -> None:
    state = LearnerState()
    assert state.overall_progress() == 0.0


def test_learner_state_overall_progress_single_concept() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    cm = ConceptMastery(
        concept_id="c1",
        mastery_score=1.0,
        retention_score=1.0,
        weight=1.0,
        last_reviewed_at=now,
    )
    state = LearnerState(mastery={"c1": cm})
    assert state.overall_progress(at=now) == pytest.approx(1.0)


def test_learner_state_overall_progress_weighted_multi_concept() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    cm1 = ConceptMastery(
        concept_id="c1",
        mastery_score=1.0,
        retention_score=0.5,
        weight=1.0,
        last_reviewed_at=now,
    )
    cm2 = ConceptMastery(
        concept_id="c2",
        mastery_score=0.5,
        retention_score=1.0,
        weight=3.0,
        last_reviewed_at=now,
    )
    state = LearnerState(mastery={"c1": cm1, "c2": cm2})

    # Weighted sum: (1.0 * 1.0 * 0.5 + 3.0 * 0.5 * 1.0) / (1.0 + 3.0) = (0.5 + 1.5) / 4.0 = 2.0 / 4.0 = 0.5
    assert state.overall_progress(at=now) == pytest.approx(0.5)


def test_learner_state_review_due_aggregate() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    cm1 = ConceptMastery(concept_id="c1", next_review_at=now + timedelta(days=2))
    cm2 = ConceptMastery(concept_id="c2", next_review_at=now - timedelta(hours=1))

    state = LearnerState(mastery={"c1": cm1})
    assert not state.review_due(at=now)

    state.mastery["c2"] = cm2
    assert state.review_due(at=now)


# --- ErrorRecord & PlanItem & DailyPlan Tests ---


def test_error_record_validation() -> None:
    err = ErrorRecord(
        code="ERR_LE_GUO_CONFUSION",
        concept_id="c1",
        occurrences=2,
        examples=["我吃过了 -> 我吃了"],
    )
    assert err.code == "ERR_LE_GUO_CONFUSION"
    assert err.occurrences == 2
    assert len(err.examples) == 1

    with pytest.raises(ValidationError):
        ErrorRecord(code="", concept_id="c1")
    with pytest.raises(ValidationError):
        ErrorRecord(code="E1", concept_id="")
    with pytest.raises(ValidationError):
        ErrorRecord(code="E1", concept_id="c1", occurrences=0)


def test_plan_item_and_daily_plan_validation() -> None:
    learner_id = uuid4()
    item = PlanItem(
        concept_id="c1",
        kind=PlanItemKind.NEW,
        objective="Learn particle 吗",
        estimated_minutes=15,
    )
    assert isinstance(item.id, UUID)
    assert not item.completed

    plan = DailyPlan(
        learner_id=learner_id,
        status=PlanStatus.ACTIVE,
        items=[item],
        rationale="Daily practice session targeting new grammar.",
    )
    assert plan.learner_id == learner_id
    assert len(plan.items) == 1
    assert plan.status == PlanStatus.ACTIVE

    # Empty items list should raise ValidationError
    with pytest.raises(ValidationError):
        DailyPlan(
            learner_id=learner_id,
            items=[],
            rationale="Rationale",
        )

    # Empty rationale should raise ValidationError
    with pytest.raises(ValidationError):
        DailyPlan(
            learner_id=learner_id,
            items=[item],
            rationale="",
        )


# --- Exercise, GradingResult, Submission Tests ---


def test_exercise_and_grading_models() -> None:
    ex = Exercise(
        concept_id="c_hsk1_ma",
        prompt="Translate: Are you a teacher?",
        target_instruction="Use 吗 in the question.",
        hsk_level=1,
        reference_answers=["你是老师吗？", "你是老师吗"],
    )
    assert ex.hsk_level == 1
    assert len(ex.reference_answers) == 2

    sub = AnswerSubmission(
        learner_id=uuid4(),
        exercise_id=ex.id,
        answer="你是老师吗？",
    )
    assert sub.exercise_id == ex.id

    scores = RubricScores(
        grammatical_correctness=1.0,
        semantic_precision=1.0,
        pragmatic_appropriateness=1.0,
    )

    result = GradingResult(
        exercise_id=ex.id,
        scores=scores,
        passed_gates=True,
        confidence=0.98,
        feedback="Perfect sentence structure!",
        detected_errors=[],
    )
    assert result.passed_gates
    assert result.confidence == 0.98
    assert result.grader_version == "v1.0.0"


# --- SessionSummary & ProgressUpdate Tests ---


def test_session_summary_and_progress_update() -> None:
    now = utc_now()
    session = SessionSummary(
        started_at=now - timedelta(minutes=20),
        ended_at=now,
        concepts_covered=["c1", "c2"],
        summary="Completed daily review and new concept.",
    )
    assert len(session.concepts_covered) == 2

    delta = ConceptDelta(
        concept_id="c1",
        previous_mastery=0.5,
        new_mastery=0.8,
        previous_retention=0.6,
        new_retention=1.0,
        next_review_at=now + timedelta(days=2),
    )
    update = ProgressUpdate(
        learner_id=uuid4(),
        exercise_id=uuid4(),
        concept_delta=delta,
        error_codes_added=["ERR_PUNCTUATION"],
        plan_invalidated=False,
    )
    assert update.concept_delta.new_mastery == 0.8
    assert not update.plan_invalidated


# --- RetrievalRequest Conditional Validation Tests ---


def test_retrieval_request_exact_mode_validation() -> None:
    learner_id = uuid4()
    # Exact mode with concept_id is valid
    req = RetrievalRequest(
        mode=RetrievalMode.EXACT,
        learner_id=learner_id,
        concept_id="c1",
    )
    assert req.mode == RetrievalMode.EXACT
    assert req.concept_id == "c1"

    # Exact mode without concept_id raises ValidationError
    with pytest.raises(ValidationError, match="Exact retrieval requires a non-empty concept_id"):
        RetrievalRequest(
            mode=RetrievalMode.EXACT,
            learner_id=learner_id,
            concept_id=None,
        )

    with pytest.raises(ValidationError, match="Exact retrieval requires a non-empty concept_id"):
        RetrievalRequest(
            mode=RetrievalMode.EXACT,
            learner_id=learner_id,
            concept_id="",
        )


def test_retrieval_request_semantic_mode_validation() -> None:
    learner_id = uuid4()
    # Semantic mode with semantic_need is valid
    req = RetrievalRequest(
        mode=RetrievalMode.SEMANTIC,
        learner_id=learner_id,
        semantic_need="Exercises focusing on asking for directions",
    )
    assert req.mode == RetrievalMode.SEMANTIC
    assert req.semantic_need is not None

    # Semantic mode without semantic_need raises ValidationError
    with pytest.raises(
        ValidationError, match="Semantic retrieval requires a non-empty semantic_need"
    ):
        RetrievalRequest(
            mode=RetrievalMode.SEMANTIC,
            learner_id=learner_id,
            semantic_need=None,
        )

    with pytest.raises(
        ValidationError, match="Semantic retrieval requires a non-empty semantic_need"
    ):
        RetrievalRequest(
            mode=RetrievalMode.SEMANTIC,
            learner_id=learner_id,
            semantic_need="",
        )


def test_retrieval_request_structured_mode() -> None:
    learner_id = uuid4()
    req = RetrievalRequest(
        mode=RetrievalMode.STRUCTURED,
        learner_id=learner_id,
        hsk_level=2,
        top_k=10,
    )
    assert req.mode == RetrievalMode.STRUCTURED
    assert req.top_k == 10


# --- Full JSON Roundtrip Serialization Test ---


def test_learner_state_json_roundtrip_serialization() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    learner_id = uuid4()
    goal = LearningGoal(
        title="Pass HSK 3 Exam",
        target_hsk_level=3,
        daily_available_minutes=25,
        created_at=now,
    )
    cm1 = ConceptMastery(
        concept_id="concept_grammar_1",
        mastery_score=0.85,
        retention_score=0.92,
        decay_lambda=0.04,
        evidence_count=5,
        interval_days=3.5,
        last_reviewed_at=now,
        next_review_at=now + timedelta(days=3),
        weight=2.0,
    )
    error = ErrorRecord(
        code="ERR_WORD_ORDER",
        concept_id="concept_grammar_1",
        occurrences=3,
        last_seen_at=now,
        examples=["我吃苹果昨天 -> 我昨天吃苹果"],
    )
    plan_item = PlanItem(
        concept_id="concept_grammar_1",
        kind=PlanItemKind.REVIEW,
        objective="Review time word placement in SVO sentences",
        estimated_minutes=10,
        completed=True,
    )
    daily_plan = DailyPlan(
        learner_id=learner_id,
        date=now,
        status=PlanStatus.ACTIVE,
        items=[plan_item],
        rationale="Spaced review for high-error concept.",
        generated_at=now,
    )
    session = SessionSummary(
        started_at=now - timedelta(minutes=25),
        ended_at=now,
        concepts_covered=["concept_grammar_1"],
        summary="Focused practice on time adverbs.",
    )

    original_state = LearnerState(
        learner_id=learner_id,
        goal=goal,
        goal_changed=False,
        mastery={"concept_grammar_1": cm1},
        error_profile=[error],
        active_plan=daily_plan,
        sessions=[session],
        updated_at=now,
    )

    json_str = original_state.model_dump_json()
    reconstructed_state = LearnerState.model_validate_json(json_str)

    assert reconstructed_state.learner_id == original_state.learner_id
    assert reconstructed_state.goal is not None
    assert reconstructed_state.goal.title == "Pass HSK 3 Exam"
    assert reconstructed_state.goal.target_hsk_level == 3
    assert len(reconstructed_state.mastery) == 1
    assert reconstructed_state.mastery["concept_grammar_1"].mastery_score == pytest.approx(0.85)
    assert reconstructed_state.mastery["concept_grammar_1"].retention_score == pytest.approx(0.92)
    assert reconstructed_state.mastery["concept_grammar_1"].weight == pytest.approx(2.0)
    assert len(reconstructed_state.error_profile) == 1
    assert reconstructed_state.error_profile[0].code == "ERR_WORD_ORDER"
    assert reconstructed_state.active_plan is not None
    assert reconstructed_state.active_plan.status == PlanStatus.ACTIVE
    assert reconstructed_state.active_plan.items[0].completed is True
    assert len(reconstructed_state.sessions) == 1
    assert reconstructed_state.sessions[0].summary == "Focused practice on time adverbs."


def test_domain_base_model_config() -> None:
    # validate_assignment check
    goal = LearningGoal(title="Initial Goal")
    with pytest.raises(ValidationError):
        goal.target_hsk_level = 10  # invalid > 6
