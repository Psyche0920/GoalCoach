"""Deterministic goal planning for GoalCoach.

This module consumes the existing LearnerState domain model and produces
an ordered DailyPlan. It does not access databases, call an LLM, or mutate
the learner state.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

from goalcoach.domain.enums import PlanItemKind, PlanStatus
from goalcoach.domain.models import (
    ConceptMastery,
    DailyPlan,
    LearnerState,
    PlanItem,
    utc_now,
)

DEFAULT_ITEM_MINUTES = 5
REMEDIAL_MASTERY_THRESHOLD = 0.60

HSK1_CONCEPT_IDS: tuple[str, ...] = tuple(
    f"hsk1_c{number:02d}" for number in range(1, 21)
)


class DeterministicGoalPlanner:
    """Create daily plans using deterministic learner-state rules."""

    def __init__(
        self,
        concept_ids: Sequence[str] = HSK1_CONCEPT_IDS,
        item_minutes: int = DEFAULT_ITEM_MINUTES,
        remedial_threshold: float = REMEDIAL_MASTERY_THRESHOLD,
        now_provider: Callable[[], datetime] = utc_now,
    ) -> None:
        if not concept_ids:
            raise ValueError("concept_ids must not be empty")

        if item_minutes <= 0:
            raise ValueError("item_minutes must be positive")

        if not 0.0 <= remedial_threshold <= 1.0:
            raise ValueError(
                "remedial_threshold must be between 0.0 and 1.0"
            )

        self._concept_ids = tuple(concept_ids)
        self._item_minutes = item_minutes
        self._remedial_threshold = remedial_threshold
        self._now_provider = now_provider

    async def create_plan(self, state: LearnerState) -> DailyPlan:
        """Create an ordered REVIEW -> REMEDIAL -> NEW daily plan."""

        if state.goal is None:
            raise ValueError(
                "A LearningGoal is required before creating a daily plan"
            )

        now = self._now_provider()
        available_minutes = state.goal.daily_available_minutes

        due_concepts = self._find_due_concepts(state, now)
        due_ids = {mastery.concept_id for mastery in due_concepts}

        remedial_concepts = self._find_remedial_concepts(
            state=state,
            excluded_concept_ids=due_ids,
        )

        new_concept_ids = self._find_new_concepts(state)

        candidates: list[tuple[str, PlanItemKind, str]] = []

        for mastery in due_concepts:
            candidates.append(
                (
                    mastery.concept_id,
                    PlanItemKind.REVIEW,
                    "Review this concept because its scheduled review is due.",
                )
            )

        for mastery in remedial_concepts:
            candidates.append(
                (
                    mastery.concept_id,
                    PlanItemKind.REMEDIAL,
                    "Strengthen this concept because its mastery score is low.",
                )
            )

        for concept_id in new_concept_ids:
            candidates.append(
                (
                    concept_id,
                    PlanItemKind.NEW,
                    "Learn the next concept in the HSK1 curriculum sequence.",
                )
            )

        if not candidates:
            fallback = self._find_lowest_retention_concept(state, now)

            if fallback is None:
                raise ValueError(
                    "Cannot create a plan without curriculum concepts"
                )

            candidates.append(
                (
                    fallback.concept_id,
                    PlanItemKind.REVIEW,
                    "Maintain the concept with the lowest current retention.",
                )
            )

        items = self._allocate_time(
            candidates=candidates,
            available_minutes=available_minutes,
        )

        return DailyPlan(
            learner_id=state.learner_id,
            date=now,
            status=PlanStatus.ACTIVE,
            items=items,
            rationale=self._build_rationale(items, available_minutes),
            generated_at=now,
        )

    def _find_due_concepts(
        self,
        state: LearnerState,
        now: datetime,
    ) -> list[ConceptMastery]:
        """Return due concepts ordered by earliest review date."""

        due = [
            mastery
            for mastery in state.mastery.values()
            if mastery.is_review_due(now)
        ]

        return sorted(
            due,
            key=lambda mastery: (
                mastery.next_review_at or now,
                mastery.current_retention(now),
                mastery.concept_id,
            ),
        )

    def _find_remedial_concepts(
        self,
        state: LearnerState,
        excluded_concept_ids: set[str],
    ) -> list[ConceptMastery]:
        """Return learned but weak concepts ordered by mastery score."""

        remedial = [
            mastery
            for mastery in state.mastery.values()
            if mastery.concept_id not in excluded_concept_ids
            and mastery.evidence_count > 0
            and mastery.mastery_score < self._remedial_threshold
        ]

        return sorted(
            remedial,
            key=lambda mastery: (
                mastery.mastery_score,
                -mastery.evidence_count,
                mastery.concept_id,
            ),
        )

    def _find_new_concepts(
        self,
        state: LearnerState,
    ) -> list[str]:
        """Return unlearned concepts in curriculum order."""

        return [
            concept_id
            for concept_id in self._concept_ids
            if concept_id not in state.mastery
        ]

    def _find_lowest_retention_concept(
        self,
        state: LearnerState,
        now: datetime,
    ) -> ConceptMastery | None:
        """Return the learned concept with the lowest current retention."""

        if not state.mastery:
            return None

        return min(
            state.mastery.values(),
            key=lambda mastery: (
                mastery.current_retention(now),
                mastery.mastery_score,
                mastery.concept_id,
            ),
        )

    def _allocate_time(
        self,
        candidates: list[tuple[str, PlanItemKind, str]],
        available_minutes: int,
    ) -> list[PlanItem]:
        """Fill the daily time budget without exceeding it."""

        items: list[PlanItem] = []
        remaining_minutes = available_minutes

        for concept_id, kind, objective in candidates:
            if remaining_minutes <= 0:
                break

            estimated_minutes = min(
                self._item_minutes,
                remaining_minutes,
            )

            items.append(
                PlanItem(
                    concept_id=concept_id,
                    kind=kind,
                    objective=objective,
                    estimated_minutes=estimated_minutes,
                )
            )

            remaining_minutes -= estimated_minutes

        return items

    @staticmethod
    def _build_rationale(
        items: list[PlanItem],
        available_minutes: int,
    ) -> str:
        """Create a human-readable explanation of the plan."""

        review_count = sum(
            item.kind == PlanItemKind.REVIEW for item in items
        )
        remedial_count = sum(
            item.kind == PlanItemKind.REMEDIAL for item in items
        )
        new_count = sum(
            item.kind == PlanItemKind.NEW for item in items
        )

        return (
            f"Created a {available_minutes}-minute deterministic plan: "
            f"{review_count} review, "
            f"{remedial_count} remedial, "
            f"{new_count} new item(s). "
            "Due reviews are prioritized before weak and new concepts."
        )


__all__ = [
    "DeterministicGoalPlanner",
    "HSK1_CONCEPT_IDS",
]