"""Deterministic ContentService querying curriculum Database #1 (goalcoach_hsk1_learning.db).

Provides sub-millisecond querying of concepts, teaching cards, exercises, and prerequisite
relationships without vector drift or embedding overhead.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from goalcoach.infrastructure.persistence.models import (
        ContentExercise,
        CurriculumConcept,
        TeachingCard,
    )
    from goalcoach.infrastructure.persistence.repositories import ContentRepository

logger = logging.getLogger(__name__)


class ContentService:
    """Deterministic, grounded gatekeeper for all curriculum materials."""

    def __init__(self, content_repo: ContentRepository) -> None:
        self._repo = content_repo

    def get_concept(self, concept_id: str) -> CurriculumConcept | None:
        """Fetch a single curriculum concept by ID, slug, or title."""
        return self._repo.get_concept(concept_id)

    def list_all_concepts(self, hsk_level: int = 1) -> list[CurriculumConcept]:
        """List all active curriculum concepts in sequence order for a given HSK level."""
        return self._repo.list_concepts(hsk_level=hsk_level)

    def get_teaching_cards(self, concept_id: str) -> list[TeachingCard]:
        """Fetch all teaching cards ordered for a concept."""
        return self._repo.get_teaching_cards(concept_id)

    def get_examples(self, concept_id: str) -> list[TeachingCard]:
        """Fetch cards that contain bilingual examples for a concept."""
        cards = self._repo.get_teaching_cards(concept_id)
        # Filter for cards that include concrete examples
        example_cards = [c for c in cards if c.example_zh or c.card_type in ("example", "mini_dialogue")]
        return example_cards if example_cards else cards

    def get_prerequisites(self, concept_id: str) -> list[str]:
        """Fetch all direct prerequisite concept IDs for a target concept."""
        all_prereqs = self._repo.get_prerequisites()
        return sorted(list(all_prereqs.get(concept_id, frozenset())))

    def get_all_prerequisites(self) -> Mapping[str, frozenset[str]]:
        """Return the complete prerequisite dependency graph."""
        return self._repo.get_prerequisites()

    def get_exercise(self, exercise_id: str) -> ContentExercise | None:
        """Lookup an exercise by its unique content ID."""
        return self._repo.get_exercise(exercise_id)

    def get_exercises_for_concept(
        self,
        concept_id: str,
        limit: int = 3,
        randomize: bool = False,
    ) -> list[ContentExercise]:
        """Retrieve practice exercises targeting a specific concept."""
        return self._repo.get_exercises(concept_id, limit=limit, randomize=randomize)

    def get_remedial_exercises(
        self,
        error_tag: str,
        limit: int = 5,
    ) -> list[ContentExercise]:
        """Query targeted remedial exercises cataloged under a specific error taxonomy tag."""
        return self._repo.get_remedial_exercises(error_tag, limit=limit)


__all__ = ["ContentService"]
