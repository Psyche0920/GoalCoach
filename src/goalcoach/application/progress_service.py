"""Deterministic Progress Service for state mutations, mastery calculations, and retention decay."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta

from goalcoach.domain.models import (
    ConceptMastery,
    ErrorRecord,
    GradingResult,
    LearnerState,
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
        else:
            mastery.mastery_score = max(0.0, min(1.0, round(mastery.mastery_score - 0.10, 4)))
            mastery.interval_days = 1.0
            mastery.next_review_at = now + timedelta(days=1.0)

            # Record mistake exercise ID
            ex_id = str(result.exercise_id)
            if ex_id not in state.today_mistake_exercise_ids:
                state.today_mistake_exercise_ids.append(ex_id)

            # Log detected error codes
            error_codes = result.detected_errors if result.detected_errors else [f"ERR_UNSPECIFIED_{concept_id}"]
            for code in error_codes:
                self._record_error(state, code=code, concept_id=concept_id, at=now)

        mastery.last_reviewed_at = now
        state.mastery[concept_id] = mastery

        if concept_id not in state.today_studied_concept_ids:
            state.today_studied_concept_ids.append(concept_id)

        # 4. Check repeated error threshold (occurrences >= 2 for the concept)
        for err in state.error_profile:
            if err.concept_id == concept_id and err.occurrences >= 2:
                state.needs_replanning = True
                logger.info(
                    "Threshold reached for error %s on concept %s (occurrences: %d); set needs_replanning=True",
                    err.code,
                    concept_id,
                    err.occurrences,
                )
                break

        state.updated_at = now
        return state

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
