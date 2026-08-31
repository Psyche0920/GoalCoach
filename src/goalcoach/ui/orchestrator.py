from enum import StrEnum

from goalcoach.domain.models import LearnerState, PlanStatus


class NextAction(StrEnum):
    PLAN_GOAL = "plan_goal"
    PLAN_REVIEW = "plan_review"
    REGENERATE_PLAN = "regenerate_plan"
    TEACH = "teach"


def route(state: LearnerState) -> NextAction:
    """Choose the next workflow deterministically using proposal priority."""
    if state.goal is None or state.goal_changed:
        return NextAction.PLAN_GOAL
    if state.review_due():
        return NextAction.PLAN_REVIEW
    if state.active_plan is None or state.active_plan.status != PlanStatus.ACTIVE:
        return NextAction.REGENERATE_PLAN
    return NextAction.TEACH
