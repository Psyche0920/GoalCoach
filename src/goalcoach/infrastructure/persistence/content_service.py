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

    def list_all_concepts(
        self,
        hsk_level: int | None = None,
        max_hsk_level: int | None = None,
    ) -> list[CurriculumConcept]:
        """List all active curriculum concepts in sequence order, optionally filtered by HSK level or max level."""
        return self._repo.list_concepts(hsk_level=hsk_level, max_hsk_level=max_hsk_level)

    def get_teaching_cards(self, concept_id: str) -> list[TeachingCard]:
        """Fetch all teaching cards ordered for a concept."""
        return self._repo.get_teaching_cards(concept_id)

    def get_examples(self, concept_id: str) -> list[TeachingCard]:
        """Fetch cards that contain bilingual examples for a concept."""
        cards = self._repo.get_teaching_cards(concept_id)
        # Filter for cards that include concrete examples
        example_cards = [
            c for c in cards if c.example_zh or c.card_type in ("example", "mini_dialogue")
        ]
        return example_cards if example_cards else cards

    def get_prerequisites(self, concept_id: str) -> list[str]:
        """Fetch all direct prerequisite concept IDs for a target concept."""
        all_prereqs = self._repo.get_prerequisites()
        return sorted(all_prereqs.get(concept_id, frozenset()))

    def get_all_prerequisites(self) -> Mapping[str, frozenset[str]]:
        """Return the complete prerequisite dependency graph."""
        return self._repo.get_prerequisites()

    def get_exercise(self, exercise_id: str) -> ContentExercise | None:
        """Lookup an exercise by its unique content ID or synthesize if auto matching."""
        repo_ex = self._repo.get_exercise(exercise_id)
        if repo_ex is not None:
            return repo_ex
        if exercise_id.endswith("_match_auto"):
            concept_id = exercise_id[:-11]
            return self.synthesize_matching_exercise(concept_id)
        return None

    def get_exercises_for_concept(
        self,
        concept_id: str,
        limit: int = 3,
        randomize: bool = False,
    ) -> list[ContentExercise]:
        """Retrieve practice exercises targeting a specific concept."""
        repo_exercises = list(self._repo.get_exercises(concept_id, limit=limit, randomize=randomize))
        concept = self.get_concept(concept_id)
        # Mix-and-match is ONLY for vocabulary concepts or concepts with explicit vocabulary focus
        if concept and (concept.concept_type == "vocabulary" or (concept.vocabulary_focus and len(concept.vocabulary_focus) >= 3)):
            matching_ex = self.get_or_synthesize_matching_exercise(concept_id)
            if matching_ex:
                existing_ids = {e.exercise_id for e in repo_exercises}
                if matching_ex.exercise_id not in existing_ids:
                    return [matching_ex] + repo_exercises
        return repo_exercises

    def get_remedial_exercises(
        self,
        error_tag: str,
        limit: int = 5,
    ) -> list[ContentExercise]:
        """Query targeted remedial exercises cataloged under a specific error taxonomy tag."""
        return self._repo.get_remedial_exercises(error_tag, limit=limit)

    def get_or_synthesize_matching_exercise(
        self,
        concept_id: str,
        count: int = 5,
    ) -> ContentExercise | None:
        """Retrieve an existing matching exercise from the database or dynamically synthesize one."""
        exercises = self._repo.get_exercises(concept_id, limit=10, randomize=False)
        for ex in exercises:
            if getattr(ex, "exercise_type", "") == "matching":
                return ex
        return self.synthesize_matching_exercise(concept_id, count=count)

    def synthesize_matching_exercise(
        self,
        concept_id: str,
        count: int = 5,
    ) -> ContentExercise | None:
        """Dynamically synthesizes a mix-and-match exercise strictly from vocabulary words."""
        import random
        from goalcoach.infrastructure.persistence.models import ContentExercise

        concept = self.get_concept(concept_id)
        if not concept:
            return None

        cards = self.get_teaching_cards(concept_id)
        vocab_items: list[tuple[str, str, str]] = []
        seen_words: set[str] = set()

        def _is_clean_vocab_word(word: str) -> bool:
            """Check that an item is a pure vocabulary word, not a grammar template or sentence."""
            if not word or len(word) > 8:
                return False
            # Exclude grammar placeholders like 'A', 'B', '+', '...', '~'
            for bad_char in ("A", "B", "C", "+", "...", "~", "？", "?", "。", "!"):
                if bad_char in word:
                    return False
            return True

        def _is_valid_english_meaning(meaning: str, word: str) -> bool:
            """Ensure meaning is genuinely English, not missing, not Chinese characters, and not the word itself."""
            if not meaning or not meaning.strip():
                return False
            meaning_str = meaning.strip()
            if meaning_str == word:
                return False
            # Meaning must contain ASCII letters
            has_ascii_alpha = any(c.isascii() and c.isalpha() for c in meaning_str)
            if not has_ascii_alpha:
                return False
            # Meaning should not be predominantly Chinese
            hanzi_count = sum(1 for c in meaning_str if '\u4e00' <= c <= '\u9fff')
            if hanzi_count > 0 and hanzi_count >= len(meaning_str) / 2:
                return False
            return True

        # 1. Collect strictly vocabulary cards (skip grammar templates / rules)
        for c in cards:
            if getattr(c, "card_type", "") in ("grammar", "pattern", "rule", "structure"):
                continue
            word = c.prompt_zh
            meaning = c.meaning_en
            pinyin = c.pinyin or ""
            if word and meaning and _is_clean_vocab_word(word) and _is_valid_english_meaning(meaning, word) and word not in seen_words:
                vocab_items.append((word, pinyin, meaning))
                seen_words.add(word)

        # 2. Add words from vocabulary_focus only if a genuine English meaning is found
        for word in (concept.vocabulary_focus or []):
            if _is_clean_vocab_word(word) and word not in seen_words:
                match_meaning = ""
                match_pinyin = ""
                for c in cards:
                    if c.prompt_zh == word or c.example_zh == word:
                        candidate = c.meaning_en or c.explanation_en or ""
                        if _is_valid_english_meaning(candidate, word):
                            match_meaning = candidate
                            match_pinyin = c.pinyin or c.example_pinyin or ""
                            break

                # If not found in concept cards, look across same-level cards
                if not match_meaning:
                    level_concepts = self.list_all_concepts(hsk_level=concept.hsk_level)
                    for other_c in level_concepts:
                        if match_meaning:
                            break
                        for oc in self.get_teaching_cards(other_c.concept_id):
                            if oc.prompt_zh == word or oc.example_zh == word:
                                candidate = oc.meaning_en or oc.explanation_en or ""
                                if _is_valid_english_meaning(candidate, word):
                                    match_meaning = candidate
                                    match_pinyin = oc.pinyin or oc.example_pinyin or ""
                                    break

                if match_meaning and _is_valid_english_meaning(match_meaning, word):
                    vocab_items.append((word, match_pinyin, match_meaning))
                    seen_words.add(word)

        # 3. Backfill from same-level vocabulary cards if needed
        if len(vocab_items) < count:
            level_concepts = self.list_all_concepts(hsk_level=concept.hsk_level)
            for other_c in level_concepts:
                if other_c.concept_id == concept_id:
                    continue
                other_cards = self.get_teaching_cards(other_c.concept_id)
                for oc in other_cards:
                    if getattr(oc, "card_type", "") in ("grammar", "pattern", "rule", "structure"):
                        continue
                    w = oc.prompt_zh
                    m = oc.meaning_en
                    p = oc.pinyin or ""
                    if w and m and _is_clean_vocab_word(w) and _is_valid_english_meaning(m, w) and w not in seen_words:
                        vocab_items.append((w, p, m))
                        seen_words.add(w)
                    if len(vocab_items) >= count:
                        break
                if len(vocab_items) >= count:
                    break

        if len(vocab_items) < 2:
            return None

        selected = vocab_items[:count]
        actual_count = len(selected)

        left_items = [
            {"id": str(i + 1), "word": word, "pinyin": pinyin}
            for i, (word, pinyin, _) in enumerate(selected)
        ]

        meanings = [(i + 1, meaning) for i, (_, _, meaning) in enumerate(selected)]
        rng = random.Random(concept_id)
        shuffled_meanings = list(meanings)
        rng.shuffle(shuffled_meanings)

        letters = ["A", "B", "C", "D", "E", "F", "G", "H"][:actual_count]
        right_items = [
            {"id": letters[idx], "meaning": meaning, "orig_index": str(orig_i)}
            for idx, (orig_i, meaning) in enumerate(shuffled_meanings)
        ]

        pairs: dict[str, str] = {}
        for r_item in right_items:
            pairs[r_item["orig_index"]] = r_item["id"]

        shorthand_answer = " ".join(f"{num}{pairs[num]}" for num in sorted(pairs.keys(), key=int))
        comma_answer = ", ".join(f"{num}-{pairs[num]}" for num in sorted(pairs.keys(), key=int))

        return ContentExercise(
            exercise_id=f"{concept_id}_match_auto",
            concept_id=concept_id,
            exercise_order=99,
            exercise_type="matching",
            prompt="Match each Chinese word with its English meaning.",
            prompt_pinyin=None,
            instruction=f"Match words 1-{actual_count} with meanings A-{letters[-1]} (e.g., {shorthand_answer}).",
            answer={"pairs": pairs},
            options={
                "left": left_items,
                "right": [{"id": r["id"], "meaning": r["meaning"]} for r in right_items],
            },
            accepted_answers=[shorthand_answer, comma_answer],
            explanation=f"Correct vocabulary pairs: {shorthand_answer}",
            target_tokens=[w for w, _, _ in selected],
            error_tags=["vocab_meaning", "matching"],
            difficulty=concept.difficulty,
            points=10,
            metadata_json={"pairs": pairs},
        )


__all__ = ["ContentService"]
