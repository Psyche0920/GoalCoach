"""Deterministic Progress Service for state mutations, mastery calculations, and retention decay."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta

from goalcoach.application.progress_reducer import reduce_concept_progress
from goalcoach.domain.enums import PlanItemKind
from goalcoach.domain.models import (
    ConceptMastery,
    ConceptProgress,
    ErrorRecord,
    GradingResult,
    LearnerState,
    LearningEvent,
    utc_now,
)
from goalcoach.infrastructure.persistence.learner_repository import SqliteLearnerRepository

logger = logging.getLogger(__name__)


class ProgressService:
    """Executes the mathematical state transitions converting grading evidence into domain updates."""

    def __init__(
        self,
        decay_lambda: float = 0.05,
        learner_repo: SqliteLearnerRepository | None = None,
    ) -> None:
        self.decay_lambda = decay_lambda
        self.learner_repo = learner_repo

    def apply_grading_result(
        self,
        state: LearnerState,
        result: GradingResult,
        concept_id: str,
        at: datetime | None = None,
        time_spent_seconds: int = 0,
    ) -> LearnerState:
        """Deterministically mutates LearnerState based on grading outcome.

        Pedagogical Rules:
        - On Pass (passed_gates is True):
          - Mastery increments by +0.25 (bounded [0.0, 1.0]).
          - Spaced interval expands by 1.8x.
          - Retention resets to 1.0.
          - Evidence count increments.
        - On Fail (passed_gates is False):
          - Mastery decrements by -0.10 (bounded [0.0, 1.0]).
          - Spaced interval resets to 1.0 day.
          - Detected error codes are logged/incremented in state.error_profile.
          - If any error occurrence for this concept reaches >= 2, state.needs_replanning is set to True.
        - Retention decays according to R(t) = R_0 * exp(-lambda * delta_t).
        """
        now = at or utc_now()

        # 1. Retrieve or initialize ConceptMastery
        mastery = state.mastery.get(concept_id)
        if mastery is None:
            mastery = ConceptMastery(
                concept_id=concept_id,
                mastery_score=0.0,
                retention_score=1.0,
                decay_lambda=self.decay_lambda,
                interval_days=1.0,
                evidence_count=0,
                last_reviewed_at=now,
            )

        # 2. Compute Retention Decay from elapsed time
        delta_days = max(0.0, (now - mastery.last_reviewed_at).total_seconds() / 86400.0)
        decayed = mastery.retention_score * math.exp(-self.decay_lambda * delta_days)
        mastery.retention_score = max(0.0, min(1.0, decayed))

        # 3. Apply Outcome Math
        if result.passed_gates:
            mastery.mastery_score = max(0.0, min(1.0, round(mastery.mastery_score + 0.25, 4)))
            mastery.interval_days = max(1.0, round(mastery.interval_days * 1.8, 2))
            mastery.retention_score = 1.0
            mastery.evidence_count += 1
            mastery.next_review_at = now + timedelta(days=mastery.interval_days)

            # Record completed exercise ID
            ex_id = str(result.exercise_id)
            if ex_id not in state.today_completed_exercise_ids:
                state.today_completed_exercise_ids.append(ex_id)

            # Check if this concept was actively in remediation
            is_remedial_item = False
            if state.active_plan:
                for item in state.active_plan.items:
                    if item.concept_id == concept_id and not item.completed:
                        if item.kind == PlanItemKind.REMEDIAL:
                            is_remedial_item = True
                        break

            if is_remedial_item and concept_id not in state.today_remediated_concept_ids:
                state.today_remediated_concept_ids.append(concept_id)

            # A correct answer resets the whole remediation counter for this
            # concept to zero (one pass clears all unresolved remediation for
            # the concept). The lifelong error history (``error_profile``) is
            # NEVER decremented or cleared.
            if concept_id in state.remediation_counters:
                state.remediation_counters.pop(concept_id, None)
            if not any(value >= 2 for value in state.remediation_counters.values()):
                state.needs_replanning = False
        else:
            mastery.mastery_score = max(0.0, min(1.0, round(mastery.mastery_score - 0.10, 4)))
            mastery.interval_days = 1.0
            mastery.next_review_at = now + timedelta(days=1.0)

            # Record mistake exercise ID
            ex_id = str(result.exercise_id)
            if ex_id not in state.today_mistake_exercise_ids:
                state.today_mistake_exercise_ids.append(ex_id)

            # Log detected error codes
            error_codes = (
                result.detected_errors
                if result.detected_errors
                else [f"ERR_UNSPECIFIED_{concept_id}"]
            )
            for code in error_codes:
                self._record_error(state, code=code, concept_id=concept_id, at=now)

            # The remediation threshold (>= 2) is tracked independently of the
            # lifelong error history: ``remediation_counters`` accumulates
            # unresolved errors until a fix is scheduled, then resets. Inside a
            # REMEDIAL (fix) item a wrong answer must NOT re-trigger
            # needs_replanning (that would create a fix -> fail -> replan ->
            # fix infinite loop), so the counter is only incremented outside it.
            in_remedial_item = False
            if state.active_plan:
                for item in state.active_plan.items:
                    if (
                        item.concept_id == concept_id
                        and not item.completed
                        and item.kind == PlanItemKind.REMEDIAL
                    ):
                        in_remedial_item = True
                        break
            if not in_remedial_item:
                current_counter = state.remediation_counters.get(concept_id, 0) + 1
                state.remediation_counters[concept_id] = current_counter
                if current_counter >= 2:
                    state.needs_replanning = True
                    logger.info(
                        "Remediation threshold reached for concept %s (counter: %d); "
                        "set needs_replanning=True",
                        concept_id,
                        current_counter,
                    )

        mastery.last_reviewed_at = now
        state.mastery[concept_id] = mastery

        self._apply_learning_evidence(
            state=state,
            result=result,
            concept_id=concept_id,
            at=now,
            time_spent_seconds=time_spent_seconds,
        )

        if concept_id not in state.today_studied_concept_ids:
            state.today_studied_concept_ids.append(concept_id)

        state.updated_at = now
        return state

    @staticmethod
    def _apply_learning_evidence(
        state: LearnerState,
        result: GradingResult,
        concept_id: str,
        at: datetime,
        time_spent_seconds: int = 0,
    ) -> None:
        """Project a graded plan interaction into roadmap progress.

        ``mastery`` drives adaptive scheduling while ``concept_progress`` drives
        the learner-facing roadmap. A grading event is authoritative evidence
        for both projections, so they must be updated in the same transaction.
        """
        active_item = next(
            (
                item
                for item in (state.active_plan.items if state.active_plan else [])
                if item.concept_id == concept_id and not item.completed
            ),
            None,
        )
        is_spaced_review = active_item is not None and active_item.kind in {
            PlanItemKind.REVIEW,
            PlanItemKind.REMEDIAL,
        }
        scores = result.scores
        quality = (
            scores.grammatical_correctness
            + scores.semantic_precision
            + scores.pragmatic_appropriateness
        ) / 3.0
        event = LearningEvent(
            learner_id=str(state.learner_id),
            plan_item_id=str(active_item.id) if active_item else "teaching_agent",
            concept_ids=[concept_id],
            event_type="review" if is_spaced_review else "attempt",
            started_at=at,
            last_active_at=at,
            active_seconds=time_spent_seconds,
            estimated_minutes=max(time_spent_seconds / 60.0, 0.0),
            engagement_score=quality,
            grading_result=result.model_dump(mode="json"),
        )
        current = state.concept_progress.get(
            concept_id,
            ConceptProgress(learner_id=str(state.learner_id), concept_id=concept_id),
        )
        current.exposed = True
        state.concept_progress[concept_id] = reduce_concept_progress(
            current,
            event,
            completes_atomic_unit=not is_spaced_review,
            is_spaced_review=is_spaced_review,
        )
        # ``ConceptMastery`` is the scheduling authority; ``ConceptProgress`` is
        # its learner-facing projection. Keep the shared mastery value identical.
        projection = state.concept_progress[concept_id]
        authority = state.mastery[concept_id]
        projection.mastery_score = authority.mastery_score
        projection.retention_at_review = authority.retention_score
        projection.decay_lambda = authority.decay_lambda
        projection.last_reviewed_at = authority.last_reviewed_at
        projection.next_review_at = authority.next_review_at

    @staticmethod
    def build_learning_event(
        state: LearnerState,
        result: GradingResult,
        concept_id: str,
        *,
        at: datetime,
        time_spent_seconds: int,
    ) -> LearningEvent:
        """Build the durable audit event matching a grading state transition."""
        active_item = next(
            (
                item
                for item in (state.active_plan.items if state.active_plan else [])
                if item.concept_id == concept_id and not item.completed
            ),
            None,
        )
        is_review = active_item is not None and active_item.kind in {
            PlanItemKind.REVIEW,
            PlanItemKind.REMEDIAL,
        }
        scores = result.scores
        quality = (
            scores.grammatical_correctness
            + scores.semantic_precision
            + scores.pragmatic_appropriateness
        ) / 3.0
        return LearningEvent(
            learner_id=str(state.learner_id),
            plan_item_id=str(active_item.id) if active_item else "teaching_agent",
            concept_ids=[concept_id],
            event_type="review" if is_review else "attempt",
            started_at=at,
            last_active_at=at,
            active_seconds=time_spent_seconds,
            estimated_minutes=max(time_spent_seconds / 60.0, 0.0),
            engagement_score=quality,
            grading_result=result.model_dump(mode="json"),
        )

    def _record_error(
        self,
        state: LearnerState,
        code: str,
        concept_id: str,
        at: datetime,
    ) -> None:
        """Append or increment an error record in the learner's error profile."""
        for existing in state.error_profile:
            if existing.code == code and existing.concept_id == concept_id:
                existing.occurrences += 1
                existing.last_seen_at = at
                return

        # Not found; append new record
        state.error_profile.append(
            ErrorRecord(
                code=code,
                concept_id=concept_id,
                occurrences=1,
                last_seen_at=at,
            )
        )

    async def apply_and_persist(
        self,
        state: LearnerState,
        result: GradingResult,
        concept_id: str,
        at: datetime | None = None,
    ) -> LearnerState:
        """Apply grading result and asynchronously persist state to SQLite WAL storage."""
        updated_state = self.apply_grading_result(state, result, concept_id, at=at)
        if self.learner_repo:
            await self.learner_repo.save(updated_state)
        return updated_state


__all__ = ["ProgressService"]
