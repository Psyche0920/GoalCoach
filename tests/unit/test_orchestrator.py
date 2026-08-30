from datetime import timedelta

from goalcoach.application.orchestrator import NextAction, route
from goalcoach.domain.models import (
    ConceptMastery,
    DailyPlan,
    LearnerState,
    LearningGoal,
    PlanItem,
    PlanItemKind,
    PlanStatus,
    utc_now,
)


def state_with_goal() -> LearnerState:
    state = LearnerState(goal=LearningGoal(title="Pass HSK1"))
    state.active_plan = DailyPlan(
        learner_id=state.learner_id,
        goal_id=state.goal.id,
        items=[
            PlanItem(
                concept_id="hsk1_grammar_ma",
                kind=PlanItemKind.NEW,
                objective="Ask a yes/no question using 吗",
                estimated_minutes=10,
            )
        ],
        rationale="First learning item",
    )
    return state


def test_new_learner_routes_to_goal_planning() -> None:
    assert route(LearnerState()) == NextAction.PLAN_GOAL


def test_due_review_has_priority_over_active_plan() -> None:
    state = state_with_goal()
    state.mastery["hsk1_grammar_ma"] = ConceptMastery(
        concept_id="hsk1_grammar_ma",
        mastery=0.8,
        retention=0.6,
        next_review_at=utc_now() - timedelta(minutes=1),
    )
    assert route(state) == NextAction.PLAN_REVIEW


def test_exhausted_plan_is_regenerated() -> None:
    state = state_with_goal()
    state.active_plan.status = PlanStatus.EXHAUSTED
    assert route(state) == NextAction.REGENERATE_PLAN


def test_active_plan_routes_to_teaching() -> None:
    assert route(state_with_goal()) == NextAction.TEACH
