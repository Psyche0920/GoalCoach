from __future__ import annotations

from typing import Protocol
from uuid import UUID

from goalcoach.domain.models import GradingResult, LearnerState, ProgressUpdate


class BackgroundStateUpdater(Protocol):
    """Runs deterministic post-answer work outside the learner response path."""

    async def enqueue(
        self,
        learner_id: UUID,
        grade: GradingResult,
    ) -> None: ...


class PlanInvalidationPolicy(Protocol):
    """Decides whether updated state requires a new plan without an LLM call."""

    def should_replan(self, state: LearnerState, update: ProgressUpdate) -> bool: ...
