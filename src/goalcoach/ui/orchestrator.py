"""Deterministic top-level workflow orchestrator and routing logic for GoalCoach."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from goalcoach.agents.interfaces import GoalPlanner, LearnerRepository
from goalcoach.domain.enums import PlanStatus
from goalcoach.domain.models import DailyPlan, LearnerState, utc_now


class LearnerNotFoundError(LookupError):
    """Raised when an orchestration request targets an unknown learner."""


class PlanningOrchestrator:
    """Coordinates deterministic plan creation and durable aggregate replacement."""

    def __init__(self, planner: GoalPlanner, repository: LearnerRepository) -> None:
        self._planner = planner
        self._repository = repository

    async def generate_daily_plan(self, learner_id: UUID) -> DailyPlan:
        """Generate and atomically persist a plan without mutating loaded state."""
        state = await self._repository.get(learner_id)
        if state is None:
            raise LearnerNotFoundError(f"Learner {learner_id} was not found")

        plan = await self._planner.create_plan(state)

        updated_state = state.model_copy(
            update={"active_plan": plan, "updated_at": utc_now()},
            deep=True,
        )

        await self._repository.save(updated_state)

        return plan


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
