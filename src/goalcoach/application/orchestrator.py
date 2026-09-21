"""Deterministic Orchestrator for GoalCoach event routing and state lifecycle management."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from pydantic import Field

from goalcoach.application.agent_history import (
    SessionLifecycleError,
    close_active_session,
    record_grading_outcome,
    record_session_started,
    record_teaching_turn,
    require_pending_teaching_turn,
)
from goalcoach.application.progress_reducer import compute_progress_summary
from goalcoach.application.progress_service import ProgressService
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
    ProgressSummary,
    TeachingAction,
    utc_now,
)
from goalcoach.infrastructure.persistence.content_service import ContentService
from goalcoach.infrastructure.persistence.learner_repository import SqliteLearnerRepository


def derive_next_action(state: LearnerState) -> str:
    """Derive the client instruction exclusively from authoritative state."""
    if state.goal is None:
        return "set_goal"
    if state.active_plan is None:
        return "plan"
    if state.active_plan.status == PlanStatus.EXHAUSTED or all(
        item.completed for item in state.active_plan.items
    ):
        return "complete"
    return "plan" if state.needs_replanning else "teach"


class PlanningWorkerPort(Protocol):
    """Application-facing contract for the Planning Agent."""

    async def create_plan(self, state: LearnerState, content_service: ContentService) -> PlanUpdate: ...


class TeachingWorkerPort(Protocol):
    """Application-facing contract for the Teaching Agent."""

    async def teach_concept(
        self,
        concept_id: str,
        state: LearnerState,
        content_service: ContentService,
        failed_attempts: int = 0,
        learner_query: str | None = None,
    ) -> TeachingAction: ...


class GraderPort(Protocol):
    """Application-facing contract for the isolated grader component."""

    async def grade(self, exercise: Exercise, answer: str) -> GradingResult: ...

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
    progress_summary: ProgressSummary | None = None
    next_action: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeterministicOrchestrator:
    """Routes inbound learner events strictly without multi-agent chaining."""

    def __init__(
        self,
        learner_repo: SqliteLearnerRepository,
        content_service: ContentService,
        progress_service: ProgressService,
        planning_worker: PlanningWorkerPort,
        teaching_worker: TeachingWorkerPort,
        grader_worker: GraderPort,
    ) -> None:
        self.learner_repo = learner_repo
        self.content_service = content_service
        self.progress_service = progress_service
        self.planning_worker = planning_worker
        self.teaching_worker = teaching_worker
        self.grader_worker = grader_worker

    def _progress_summary(self, state: LearnerState) -> ProgressSummary:
        """Return the one backend-owned progress projection for every event response."""
        return compute_progress_summary(state, self.content_service.list_all_concepts())

    async def _persist_state(self, state: LearnerState) -> None:
        """Persist one authoritative mutation and advance its monotonic version."""
        state.state_version += 1
        state.updated_at = utc_now()
        await self.learner_repo.save(state)

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
            )
            await self.learner_repo.save(state)

        match event.event_type:
            case EventType.GOAL_CREATED:
                return await self._handle_goal_created(state, event.payload)
            case EventType.SESSION_STARTED:
                return await self._handle_session_started(state, event.payload)
            case EventType.SESSION_ENDED:
                return await self._handle_session_ended(state, event.payload)
            case EventType.HELP_REQUESTED:
                return await self._handle_help_requested(state, event.payload)
            case EventType.ANSWER_SUBMITTED:
                return await self._handle_answer_submitted(state, event.payload)
            case EventType.REPLAN_REQUESTED:
                return await self._handle_replan_requested(state, event.payload)
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
        state.goal = LearningGoal(
            id=current_goal.id,
            title=title,
            target_hsk_level=target_hsk_level,
            daily_available_minutes=daily_minutes,
        )
        state.needs_replanning = False
        # A changed free-form goal owns a newly selected roadmap. Historical
        # learning evidence remains intact and can still inform the new plan.
        state.roadmap_concept_ids = []

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
        state.roadmap_concept_ids = plan_update.roadmap_concept_ids
        state.roadmap_adjustments = plan_update.roadmap_adjustments
        await self._persist_state(state)

        return OrchestratorResponse(
            event_type=EventType.GOAL_CREATED,
            learner_id=state.learner_id,
            plan_update=plan_update,
            daily_plan=daily_plan,
            state=state,
            progress_summary=self._progress_summary(state),
            next_action=derive_next_action(state),
        )

    async def _handle_session_started(
        self,
        state: LearnerState,
        payload: dict[str, Any],
    ) -> OrchestratorResponse:
        """Process SESSION_STARTED: verify active plan and call Teaching Agent for active item."""
        if state.goal is None:
            raise SessionLifecycleError("Create a learning goal before starting a session")
        plan = state.active_plan
        if (
            plan is not None
            and plan.status == PlanStatus.EXHAUSTED
            and plan.date.date() == utc_now().date()
        ):
            return OrchestratorResponse(
                event_type=EventType.SESSION_STARTED,
                learner_id=state.learner_id,
                daily_plan=plan,
                state=state,
                progress_summary=self._progress_summary(state),
                next_action=derive_next_action(state),
            )
        planned_minutes = payload.get("preferred_duration_minutes") or (
            state.goal.daily_available_minutes
        )
        record_session_started(
            state,
            planned_minutes=planned_minutes,
            focus=payload.get("session_focus"),
        )
        plan = state.active_plan
        plan_needs_regen = (
            plan is None
            or plan.status == PlanStatus.INVALID
            or plan.date.date() != utc_now().date()
            or state.needs_replanning
            or sum(item.estimated_minutes for item in plan.items) > planned_minutes
        )

        replanned = False
        if plan_needs_regen:
            plan_update: PlanUpdate
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
            state.roadmap_concept_ids = plan_update.roadmap_concept_ids
            state.roadmap_adjustments = plan_update.roadmap_adjustments
            state.needs_replanning = False
            replanned = True
            await self._persist_state(state)
            return OrchestratorResponse(
                event_type=EventType.SESSION_STARTED,
                learner_id=state.learner_id,
                plan_update=plan_update,
                daily_plan=plan,
                replanned=True,
                state=state,
                progress_summary=self._progress_summary(state),
                next_action=derive_next_action(state),
            )

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

        record_teaching_turn(state, teaching_action)
        await self._persist_state(state)

        return OrchestratorResponse(
            event_type=EventType.SESSION_STARTED,
            learner_id=state.learner_id,
            daily_plan=plan,
            teaching_action=teaching_action,
            replanned=replanned,
            state=state,
            progress_summary=self._progress_summary(state),
            next_action=derive_next_action(state),
        )

    async def _handle_session_ended(
        self,
        state: LearnerState,
        payload: dict[str, Any],
    ) -> OrchestratorResponse:
        """Close the active session and persist its bounded summary."""
        summary = close_active_session(
            state,
            additional_active_seconds=payload.get("additional_active_seconds", 0),
        )
        await self._persist_state(state)
        return OrchestratorResponse(
            event_type=EventType.SESSION_ENDED,
            learner_id=state.learner_id,
            daily_plan=state.active_plan,
            state=state,
            progress_summary=self._progress_summary(state),
            next_action=derive_next_action(state),
            metadata={"sessionSummary": summary.model_dump(mode="json", by_alias=True)},
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

        record_teaching_turn(state, teaching_action, learner_query=learner_query)
        await self._persist_state(state)

        return OrchestratorResponse(
            event_type=EventType.HELP_REQUESTED,
            learner_id=state.learner_id,
            teaching_action=teaching_action,
            state=state,
            progress_summary=self._progress_summary(state),
            next_action=derive_next_action(state),
        )

    async def _handle_answer_submitted(
        self,
        state: LearnerState,
        payload: dict[str, Any],
    ) -> OrchestratorResponse:
        """Grade one pending exercise and persist its deterministic state transition."""
        exercise_id = payload["exercise_id"]
        concept_id = payload["concept_id"]
        answer = payload["answer"]

        # 1. Fetch exercise definition from content service
        content_ex = self.content_service.get_exercise(exercise_id)
        if content_ex:
            ref_answers = list(content_ex.accepted_answers) if content_ex.accepted_answers else []
            ans_val = (
                content_ex.answer.get("value")
                if isinstance(content_ex.answer, dict)
                else str(content_ex.answer or "")
            )
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

        require_pending_teaching_turn(
            state,
            concept_id=concept_id,
            exercise_id=str(exercise_id),
        )

        # 2. Grade answer via Grader Component
        grading_result = await self.grader_worker.grade(exercise=exercise, answer=answer)

        # 3. Apply state mutations via Progress Service
        occurred_at = utc_now()
        time_spent_seconds = payload.get("time_spent_seconds", 0)
        learning_event = self.progress_service.build_learning_event(
            state,
            grading_result,
            concept_id,
            at=occurred_at,
            time_spent_seconds=time_spent_seconds,
        )
        state = self.progress_service.apply_grading_result(
            state=state,
            result=grading_result,
            concept_id=concept_id,
            at=occurred_at,
            time_spent_seconds=time_spent_seconds,
        )
        record_grading_outcome(
            state,
            concept_id=concept_id,
            exercise_id=str(exercise_id),
            result=grading_result,
            time_spent_seconds=time_spent_seconds,
        )

        # If answer passed, mark item completed in active plan
        if grading_result.passed_gates and state.active_plan:
            for item in state.active_plan.items:
                if item.concept_id == concept_id and not item.completed:
                    item.completed = True
                    break
            if all(item.completed for item in state.active_plan.items):
                state.active_plan.status = PlanStatus.EXHAUSTED

        # 4. Replanning gate: ProgressService marks the state only. Planning runs
        # on the next SESSION_STARTED or explicit REPLAN_REQUESTED event, keeping
        # the one-reasoning-worker-per-event invariant intact.
        replanned = False
        plan_update: PlanUpdate | None = None

        await self.learner_repo.record_learning_event(learning_event)
        await self._persist_state(state)

        return OrchestratorResponse(
            event_type=EventType.ANSWER_SUBMITTED,
            learner_id=state.learner_id,
            grading_result=grading_result,
            plan_update=plan_update,
            daily_plan=state.active_plan,
            replanned=replanned,
            state=state,
            progress_summary=self._progress_summary(state),
            next_action=derive_next_action(state),
        )

    async def _handle_replan_requested(
        self,
        state: LearnerState,
        payload: dict[str, Any],
    ) -> OrchestratorResponse:
        """Regenerate the daily plan through one explicit Planning Agent event."""
        if state.goal is None:
            raise SessionLifecycleError("Create a learning goal before requesting a new plan")
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
        state.roadmap_concept_ids = plan_update.roadmap_concept_ids
        state.roadmap_adjustments = plan_update.roadmap_adjustments
        state.needs_replanning = False
        remediated_ids = {
            item.concept_id for item in plan.items if item.kind == PlanItemKind.REMEDIAL
        }
        for concept_id in remediated_ids:
            state.remediation_counters.pop(concept_id, None)
        await self._persist_state(state)
        return OrchestratorResponse(
            event_type=EventType.REPLAN_REQUESTED,
            learner_id=state.learner_id,
            plan_update=plan_update,
            daily_plan=plan,
            replanned=True,
            state=state,
            progress_summary=self._progress_summary(state),
            next_action=derive_next_action(state),
            metadata={"reason": payload.get("reason")},
        )

__all__ = [
    "DeterministicOrchestrator",
    "OrchestratorResponse",
    "derive_next_action",
]
