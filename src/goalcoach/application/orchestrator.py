"""Deterministic Orchestrator for GoalCoach event routing and state lifecycle management."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from pydantic import Field

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
    PlanItem,
    PlanUpdate,
    TeachingAction,
    utc_now,
)
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
        planning_worker: Any | None = None,
        teaching_worker: Any | None = None,
        grader_worker: Any | None = None,
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
                goal=LearningGoal(
                    title="HSK 1 Complete Goal", target_hsk_level=1, daily_available_minutes=20
                ),
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

        plan_update: PlanUpdate | None = None
        if self.planning_worker:
            plan_update = await self.planning_worker.create_plan(
                state=state,
                content_service=self.content_service,
            )
        else:
            # Fallback deterministic initial plan
            plan_update = self._deterministic_fallback_plan(state)

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
            plan_update: PlanUpdate
            if self.planning_worker:
                plan_update = await self.planning_worker.create_plan(
                    state=state,
                    content_service=self.content_service,
                )
            else:
                plan_update = self._deterministic_fallback_plan(state)

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
        teaching_action: TeachingAction
        if self.teaching_worker:
            teaching_action = await self.teaching_worker.teach_concept(
                concept_id=concept_id,
                state=state,
                content_service=self.content_service,
                failed_attempts=failed_attempts,
            )
        else:
            teaching_action = self._deterministic_fallback_teaching_action(concept_id)

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

        teaching_action: TeachingAction
        if self.teaching_worker:
            teaching_action = await self.teaching_worker.teach_concept(
                concept_id=concept_id,
                state=state,
                content_service=self.content_service,
                failed_attempts=1,  # Signal confusion to trigger HINT or CONTRAST_EXAMPLE
                learner_query=learner_query,
            )
        else:
            teaching_action = self._deterministic_fallback_help_action(concept_id)

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
                options=content_ex.options,
                hsk_level=1,
            )
        else:
            raise ValueError(
                f"Unknown exercise_id {exercise_id!r}; answers can only be graded "
                "against canonical curriculum exercises"
            )

        # 2. Grade answer via Grader Component
        grading_result: GradingResult
        if self.grader_worker:
            grading_result = await self.grader_worker.grade(exercise=exercise, answer=answer)
        else:
            grading_result = self._deterministic_fallback_grade(exercise, answer)

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
            logger.info(
                "needs_replanning is True for learner %s; invoking Planning Agent", state.learner_id
            )
            if self.planning_worker:
                plan_update = await self.planning_worker.create_plan(
                    state=state,
                    content_service=self.content_service,
                )
            else:
                plan_update = self._deterministic_fallback_plan(state)

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

    def _deterministic_fallback_plan(self, state: LearnerState) -> PlanUpdate:
        """Deterministic plan generation if LLM planning worker is not injected."""
        all_concepts = self.content_service.list_all_concepts()
        concept_ids = [c.concept_id for c in all_concepts] or ["hsk1_c01", "hsk1_c02"]
        items: list[PlanItem] = []

        # Remedial candidates: exclude already remediated concepts today
        remedial_candidates: list[str] = []
        if state.error_profile:
            for err in state.error_profile:
                if (
                    err.concept_id not in state.today_remediated_concept_ids
                    and err.concept_id not in remedial_candidates
                ):
                    remedial_candidates.append(err.concept_id)

        for cid, m in state.mastery.items():
            if (
                m.mastery_score < 0.60
                and cid not in state.today_remediated_concept_ids
                and cid not in state.today_studied_concept_ids
                and cid not in remedial_candidates
            ):
                remedial_candidates.append(cid)

        for remedial_concept in remedial_candidates:
            items.append(
                PlanItem(
                    concept_id=remedial_concept,
                    kind=PlanItemKind.REMEDIAL,
                    objective=f"Remediate recurring weakness in {remedial_concept}",
                    estimated_minutes=10,
                )
            )
            if len(items) >= 2:
                break

        # Due reviews
        for cid, mastery in state.mastery.items():
            if mastery.is_review_due() and cid not in [it.concept_id for it in items]:
                items.append(
                    PlanItem(
                        concept_id=cid,
                        kind=PlanItemKind.REVIEW,
                        objective=f"Review due concept {cid}",
                        estimated_minutes=5,
                    )
                )

        # New concepts (respecting prerequisites and DAG dependencies)
        prereq_graph = self.content_service.get_all_prerequisites()
        for cid in concept_ids:
            if cid not in state.mastery and cid not in [it.concept_id for it in items]:
                prereqs = prereq_graph.get(cid, frozenset())
                prereqs_met = all(
                    (
                        p in state.mastery
                        and (
                            state.mastery[p].mastery_score >= 0.50
                            or p in state.today_remediated_concept_ids
                        )
                    )
                    for p in prereqs
                )
                if prereqs_met:
                    items.append(
                        PlanItem(
                            concept_id=cid,
                            kind=PlanItemKind.NEW,
                            objective=f"Learn new HSK1 concept {cid}",
                            estimated_minutes=5,
                        )
                    )
            if len(items) >= 3:
                break

        if not items:
            items.append(
                PlanItem(
                    concept_id=concept_ids[0],
                    kind=PlanItemKind.NEW,
                    objective="Introductory HSK1 concept",
                    estimated_minutes=5,
                )
            )

        total_min = sum(it.estimated_minutes for it in items)
        return PlanUpdate(
            daily_allocation_minutes=total_min,
            ordered_items=items,
            adaptation_rationale=f"Deterministic allocation with {len(items)} items.",
        )

    def _deterministic_fallback_teaching_action(self, concept_id: str) -> TeachingAction:
        from goalcoach.domain.enums import TeachingActionKind

        concept = self.content_service.get_concept(concept_id)
        cards = self.content_service.get_teaching_cards(concept_id)
        content = cards[0].content if cards else (concept.title_zh if concept else "你好")
        pinyin = cards[0].pinyin if cards else "nǐ hǎo"
        return TeachingAction(
            action_kind=TeachingActionKind.EXPLANATION,
            concept_id=concept_id,
            content=f"Let's focus on: {content}",
            pinyin=pinyin,
        )

    def _deterministic_fallback_help_action(self, concept_id: str) -> TeachingAction:
        from goalcoach.domain.enums import TeachingActionKind

        return TeachingAction(
            action_kind=TeachingActionKind.CONTRAST_EXAMPLE,
            concept_id=concept_id,
            content="Notice the word order pattern: Subject + Verb + Object + 吗?",
            pinyin="ma?",
        )

    def _deterministic_fallback_grade(self, exercise: Exercise, answer: str) -> GradingResult:
        from uuid import uuid4

        from goalcoach.domain.models import RubricScores

        clean_answer = answer.strip()
        accepted = [a.strip() for a in exercise.reference_answers]
        resolved = clean_answer
        if exercise.options:
            if clean_answer.isdigit():
                idx = int(clean_answer) - 1
                if 0 <= idx < len(exercise.options):
                    resolved = exercise.options[idx].strip()
            elif clean_answer.upper() in ("A", "B", "C", "D"):
                idx = ord(clean_answer.upper()) - ord("A")
                if 0 <= idx < len(exercise.options):
                    resolved = exercise.options[idx].strip()

        passed = clean_answer in accepted or resolved in accepted
        score = 1.0 if passed else 0.4
        return GradingResult(
            exercise_id=exercise.id or uuid4(),
            scores=RubricScores(
                grammatical_correctness=score,
                semantic_precision=score,
                pragmatic_appropriateness=score,
            ),
            passed_gates=passed,
            confidence=1.0,
            feedback="Correct!" if passed else "Please check sentence structure and particles.",
            detected_errors=[] if passed else [f"ERR_{exercise.concept_id.upper()}"],
        )


__all__ = [
    "DeterministicOrchestrator",
    "OrchestratorResponse",
]
