"""Deterministic top-level workflow orchestrator and routing logic for GoalCoach."""

from __future__ import annotations

from enum import StrEnum

from goalcoach.domain.enums import PlanStatus
from goalcoach.domain.models import LearnerState


class NextAction(StrEnum):
    """The next deterministic action or workflow branch to execute."""

    PLAN_GOAL = "plan_goal"
    PLAN_REVIEW = "plan_review"
    REGENERATE_PLAN = "regenerate_plan"
    TEACH = "teach"


def route(state: LearnerState) -> NextAction:
    """Deterministically routes the learner's state to the next action based on priority rules.

    Priority Rules:
        1. Goal Planning: If `state.goal is None` or `state.goal_changed` is True, returns `NextAction.PLAN_GOAL`.
        2. Spaced Review: If `state.review_due()` is True, returns `NextAction.PLAN_REVIEW`.
        3. Plan Regeneration: If `state.active_plan is None` or `state.active_plan.status != PlanStatus.ACTIVE`,
           returns `NextAction.REGENERATE_PLAN`.
        4. Interactive Teaching (Default): Otherwise returns `NextAction.TEACH`.

    Args:
        state: The current aggregate state of the learner.

    Returns:
        The selected `NextAction` to be handled by the execution layer.
    """
    if state.goal is None or state.goal_changed:
        return NextAction.PLAN_GOAL
    if state.review_due():
        return NextAction.PLAN_REVIEW
    if state.active_plan is None or state.active_plan.status != PlanStatus.ACTIVE:
        return NextAction.REGENERATE_PLAN
    return NextAction.TEACH
