"""Deterministic Orchestrator for GoalCoach event routing and state lifecycle management."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from pydantic import Field

from goalcoach.domain.enums import EventType, PlanItemKind, PlanStatus
from goalcoach.domain.events import InboundEvent
from goalcoach.domain.models import (
    DailyPlan,
    DomainBaseModel,
    Exercise,
    GradingResult,
    LearnerState,
    LearningGoal,
    PlanUpdate,
    TeachingAction,
    utc_now,
)
from goalcoach.application.progress_service import ProgressService
from goalcoach.infrastructure.persistence.content_service import ContentService
from goalcoach.infrastructure.persistence.learner_repository import SqliteLearnerRepository

logger = logging.getLogger(__name__)


class OrchestratorResponse(DomainBaseModel):
    """Unified response envelope returned by the Deterministic Orchestrator."""

    status: str = "success"
    event_type: EventType
    learner_id: str | UUID
    teaching_action: TeachingAction | None = None
    plan_update: PlanUpdate | None = None
    daily_plan: DailyPlan | None = None
    grading_result: GradingResult | None = None
    replanned: bool = False
    state: LearnerState | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeterministicOrchestrator:
    """Routes inbound learner events strictly without multi-agent chaining."""

    def __init__(
        self,
        learner_repo: SqliteLearnerRepository,
        content_service: ContentService,
        progress_service: ProgressService,
        planning_worker: Any,
        teaching_worker: Any,
        grader_worker: Any,
    ) -> None:
        self.learner_repo = learner_repo
        self.content_service = content_service
        self.progress_service = progress_service
        self.planning_worker = planning_worker
        self.teaching_worker = teaching_worker
        self.grader_worker = grader_worker

    async def handle_event(
        self,
        event_type: EventType | str,
        payload: dict[str, Any],
        learner_id: str | UUID,
    ) -> OrchestratorResponse:
        """Handle an inbound event according to the deterministic priority lifecycle."""
        if isinstance(event_type, str):
            event_type = EventType(event_type)

        inbound = InboundEvent(
            event_type=event_type,
            learner_id=learner_id,
            payload=payload,
            timestamp=utc_now(),
        )
        return await self.dispatch(inbound)

    async def dispatch(self, event: InboundEvent) -> OrchestratorResponse:
        """Dispatch event according to its type."""
        learner_id = str(event.learner_id)
        state = await self.learner_repo.get(learner_id)
        if state is None:
            state = LearnerState(
                learner_id=learner_id,
                display_name=f"Learner {learner_id}",
                goal=LearningGoal(title="HSK 1 Complete Goal", target_hsk_level=1, daily_available_minutes=20),
            )
            await self.learner_repo.save(state)

        match event.event_type:
            case EventType.GOAL_CREATED:
                return await self._handle_goal_created(state, event.payload)
            case EventType.SESSION_STARTED:
                return await self._handle_session_started(state, event.payload)
            case EventType.HELP_REQUESTED:
                return await self._handle_help_requested(state, event.payload)
            case EventType.ANSWER_SUBMITTED:
                return await self._handle_answer_submitted(state, event.payload)
            case _:
                raise ValueError(f"Unknown event type: {event.event_type}")

    async def _handle_goal_created(
        self,
        state: LearnerState,
        payload: dict[str, Any],
    ) -> OrchestratorResponse:
        """Process GOAL_CREATED: configure goal and call Planning Agent to generate initial plan."""
        current_goal = state.goal or LearningGoal(title="HSK 1 Goal")
        title = payload.get("title", current_goal.title)
        target_hsk_level = payload.get("target_hsk_level", current_goal.target_hsk_level)
        daily_minutes = payload.get("daily_available_minutes", current_goal.daily_available_minutes)
        context_interests = payload.get("context_interests", state.context_interests)

        state.goal = LearningGoal(
            id=current_goal.id,
            title=title,
            target_hsk_level=target_hsk_level,
            daily_available_minutes=daily_minutes,
        )
        state.context_interests = context_interests
        state.needs_replanning = False

        plan_update = await self.planning_worker.create_plan(
            state=state,
            content_service=self.content_service,
        )

        # Convert PlanUpdate to DailyPlan
        daily_plan = DailyPlan(
            learner_id=state.learner_id,
            date=utc_now(),
            status=PlanStatus.ACTIVE,
            items=plan_update.ordered_items,
            rationale=plan_update.adaptation_rationale,
            generated_at=utc_now(),
        )
        state.active_plan = daily_plan
        state.updated_at = utc_now()
        await self.learner_repo.save(state)

        return OrchestratorResponse(
            event_type=EventType.GOAL_CREATED,
            learner_id=state.learner_id,
            plan_update=plan_update,
            daily_plan=daily_plan,
            state=state,
        )

    async def _handle_session_started(
        self,
        state: LearnerState,
        payload: dict[str, Any],
    ) -> OrchestratorResponse:
        """Process SESSION_STARTED: verify active plan and call Teaching Agent for active item."""
        plan = state.active_plan
        plan_needs_regen = (
            plan is None
            or plan.status != PlanStatus.ACTIVE
            or all(item.completed for item in plan.items)
            or state.needs_replanning
        )

        replanned = False
        if plan_needs_regen:
            plan_update = await self.planning_worker.create_plan(
                state=state,
                content_service=self.content_service,
            )

            plan = DailyPlan(
                learner_id=state.learner_id,
                date=utc_now(),
                status=PlanStatus.ACTIVE,
                items=plan_update.ordered_items,
                rationale=plan_update.adaptation_rationale,
                generated_at=utc_now(),
            )
            state.active_plan = plan
            state.needs_replanning = False
            replanned = True

        # Find first uncompleted item
        active_item = next((item for item in plan.items if not item.completed), plan.items[0])
        concept_id = active_item.concept_id

        # Derive failure history for active item
        failed_attempts = sum(
            err.occurrences for err in state.error_profile if err.concept_id == concept_id
        )
        if active_item.kind == PlanItemKind.REMEDIAL and failed_attempts == 0:
            failed_attempts = 1

        # Invoke Teaching Agent
        teaching_action = await self.teaching_worker.teach_concept(
            concept_id=concept_id,
            state=state,
            content_service=self.content_service,
            failed_attempts=failed_attempts,
        )

        state.updated_at = utc_now()
        await self.learner_repo.save(state)

        return OrchestratorResponse(
            event_type=EventType.SESSION_STARTED,
            learner_id=state.learner_id,
            daily_plan=plan,
            teaching_action=teaching_action,
            replanned=replanned,
            state=state,
        )

    async def _handle_help_requested(
        self,
        state: LearnerState,
        payload: dict[str, Any],
    ) -> OrchestratorResponse:
        """Process HELP_REQUESTED: invoke Teaching Agent with failed attempt history to switch strategy."""
        concept_id = payload.get("concept_id") or "hsk1_c01"
        learner_query = payload.get("learner_query")

        teaching_action = await self.teaching_worker.teach_concept(
            concept_id=concept_id,
            state=state,
            content_service=self.content_service,
            failed_attempts=1,
            learner_query=learner_query,
        )

        return OrchestratorResponse(
            event_type=EventType.HELP_REQUESTED,
            learner_id=state.learner_id,
            teaching_action=teaching_action,
            state=state,
        )

    async def _handle_answer_submitted(
        self,
        state: LearnerState,
        payload: dict[str, Any],
    ) -> OrchestratorResponse:
        """Process ANSWER_SUBMITTED: grade submission, update state, and re-plan if needs_replanning."""
        exercise_id = payload["exercise_id"]
        concept_id = payload["concept_id"]
        answer = payload["answer"]

        # 1. Fetch exercise definition from content service
        content_ex = self.content_service.get_exercise(exercise_id)
        if content_ex:
            ref_answers = list(content_ex.accepted_answers) if content_ex.accepted_answers else []
            ans_val = content_ex.answer.get("value") if isinstance(content_ex.answer, dict) else str(content_ex.answer or "")
            if ans_val and ans_val not in ref_answers:
                ref_answers.append(ans_val)

            exercise = Exercise(
                id=content_ex.exercise_id,
                concept_id=content_ex.concept_id,
                prompt=content_ex.prompt,
                target_instruction=content_ex.instruction or "",
                reference_answers=ref_answers,
                hsk_level=1,
            )
        else:
            raise ValueError(
                f"Unknown exercise_id {exercise_id!r}; answers can only be graded "
                "against canonical curriculum exercises"
            )

        # 2. Grade answer via Grader Component
        grading_result = await self.grader_worker.grade(exercise=exercise, answer=answer)

        # 3. Apply state mutations via Progress Service
        state = self.progress_service.apply_grading_result(
            state=state,
            result=grading_result,
            concept_id=concept_id,
        )

        # If answer passed, mark item completed in active plan
        if grading_result.passed_gates and state.active_plan:
            for item in state.active_plan.items:
                if item.concept_id == concept_id and not item.completed:
                    item.completed = True
                    break

        # 4. Check replanning gate: if needs_replanning == True -> invoke Planning Agent
        replanned = False
        plan_update: PlanUpdate | None = None
        if state.needs_replanning:
            logger.info("needs_replanning is True for learner %s; invoking Planning Agent", state.learner_id)
            plan_update = await self.planning_worker.create_plan(
                state=state,
                content_service=self.content_service,
            )

            adapted_plan = DailyPlan(
                learner_id=state.learner_id,
                date=utc_now(),
                status=PlanStatus.ACTIVE,
                items=plan_update.ordered_items,
                rationale=plan_update.adaptation_rationale,
                generated_at=utc_now(),
            )
            state.active_plan = adapted_plan
            state.needs_replanning = False
            replanned = True

        state.updated_at = utc_now()
        await self.learner_repo.save(state)

        return OrchestratorResponse(
            event_type=EventType.ANSWER_SUBMITTED,
            learner_id=state.learner_id,
            grading_result=grading_result,
            daily_plan=state.active_plan,
            plan_update=plan_update,
            replanned=replanned,
            state=state,
        )

__all__ = [
    "DeterministicOrchestrator",
    "OrchestratorResponse",
]
