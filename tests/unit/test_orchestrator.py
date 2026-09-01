"""Unit test suite for the deterministic workflow orchestrator and routing rules."""

from datetime import timedelta

from goalcoach.domain.enums import PlanItemKind, PlanStatus
from goalcoach.domain.models import (
    ConceptMastery,
    DailyPlan,
    LearnerState,
    LearningGoal,
    PlanItem,
    utc_now,
)
from goalcoach.ui.orchestrator import NextAction, route


def create_state_with_active_plan() -> LearnerState:
    """Helper fixture creating a learner state with a valid goal and active plan."""
    state = LearnerState(goal=LearningGoal(title="Pass HSK 1 Exam", target_hsk_level=1))
    state.active_plan = DailyPlan(
        learner_id=state.learner_id,
        items=[
            PlanItem(
                concept_id="hsk1_grammar_ma",
                kind=PlanItemKind.NEW,
                objective="Ask a yes/no question using 吗",
                estimated_minutes=10,
            )
        ],
        rationale="Daily practice session targeting question particles.",
    )
    return state


# --- Priority 1: Goal Planning Tests ---


def test_new_learner_without_goal_routes_to_plan_goal() -> None:
    state = LearnerState()
    assert state.goal is None
    assert route(state) == NextAction.PLAN_GOAL


def test_learner_with_goal_changed_flag_routes_to_plan_goal() -> None:
    state = create_state_with_active_plan()
    state.goal_changed = True
    assert route(state) == NextAction.PLAN_GOAL


def test_goal_planning_precedence_over_review_due_and_active_plan() -> None:
    state = create_state_with_active_plan()
    state.goal_changed = True
    # Even if review is also due, goal change has highest priority
    state.mastery["hsk1_grammar_ma"] = ConceptMastery(
        concept_id="hsk1_grammar_ma",
        mastery_score=0.8,
        retention_score=0.6,
        next_review_at=utc_now() - timedelta(minutes=5),
    )
    assert route(state) == NextAction.PLAN_GOAL


# --- Priority 2: Spaced Review Tests ---


def test_expired_review_timestamp_routes_to_plan_review() -> None:
    state = create_state_with_active_plan()
    state.mastery["hsk1_grammar_ma"] = ConceptMastery(
        concept_id="hsk1_grammar_ma",
        mastery_score=0.8,
        retention_score=0.6,
        next_review_at=utc_now() - timedelta(minutes=1),
    )
    assert state.review_due() is True
    assert route(state) == NextAction.PLAN_REVIEW


def test_review_due_precedence_over_missing_or_exhausted_plan() -> None:
    state = create_state_with_active_plan()
    state.active_plan = None
    state.mastery["hsk1_grammar_ma"] = ConceptMastery(
        concept_id="hsk1_grammar_ma",
        mastery_score=0.8,
        retention_score=0.6,
        next_review_at=utc_now() - timedelta(minutes=1),
    )
    # Review due (Priority 2) takes precedence over missing plan (Priority 3)
    assert route(state) == NextAction.PLAN_REVIEW


def test_future_review_date_does_not_trigger_review_routing() -> None:
    state = create_state_with_active_plan()
    state.mastery["hsk1_grammar_ma"] = ConceptMastery(
        concept_id="hsk1_grammar_ma",
        mastery_score=0.8,
        retention_score=0.6,
        next_review_at=utc_now() + timedelta(days=2),
    )
    assert state.review_due() is False
    assert route(state) == NextAction.TEACH


# --- Priority 3: Plan Regeneration Tests ---


def test_missing_active_plan_routes_to_regenerate_plan() -> None:
    state = LearnerState(goal=LearningGoal(title="Pass HSK 1"))
    state.active_plan = None
    assert route(state) == NextAction.REGENERATE_PLAN


def test_exhausted_plan_routes_to_regenerate_plan() -> None:
    state = create_state_with_active_plan()
    assert state.active_plan is not None
    state.active_plan.status = PlanStatus.EXHAUSTED
    assert route(state) == NextAction.REGENERATE_PLAN


def test_invalid_plan_routes_to_regenerate_plan() -> None:
    state = create_state_with_active_plan()
    assert state.active_plan is not None
    state.active_plan.status = PlanStatus.INVALID
    assert route(state) == NextAction.REGENERATE_PLAN


# --- Priority 4: Default Interactive Teaching Tests ---


def test_active_plan_with_no_due_reviews_routes_to_teaching() -> None:
    state = create_state_with_active_plan()
    assert route(state) == NextAction.TEACH
