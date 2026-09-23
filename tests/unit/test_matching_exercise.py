"""Unit and integration tests for mix-and-match (matching) exercise type,
dynamic synthesis, input format parsing, and deterministic fast-path grading.
"""

from pathlib import Path

import pytest

from goalcoach.agents.grader_component import GraderComponent, parse_matching_pairs
from goalcoach.application.orchestrator import DeterministicOrchestrator
from goalcoach.domain.models import Exercise, LearningGoal
from goalcoach.infrastructure.persistence import (
    ContentRepository,
    ContentService,
    create_session_factory,
)

DATABASE_PATH = Path("data/database1/goalcoach_hsk1_learning.db")


@pytest.fixture
def content_service() -> ContentService:
    if not DATABASE_PATH.exists():
        pytest.skip("Database #1 required for matching exercise tests")
    factory = create_session_factory(f"sqlite:///{DATABASE_PATH}")
    repo = ContentRepository(factory)
    return ContentService(repo)


def test_parse_matching_pairs_formats():
    """Verify robust parsing of various human-entered matching formats."""
    expected = {"1": "C", "2": "A", "3": "D", "4": "B", "5": "E"}

    # Format 1: Shorthand
    assert parse_matching_pairs("1C 2A 3D 4B 5E") == expected
    assert parse_matching_pairs("1c 2a 3d 4b 5e") == expected

    # Format 2: Hyphenated with commas
    assert parse_matching_pairs("1-C, 2-A, 3-D, 4-B, 5-E") == expected

    # Format 3: Colon separated
    assert parse_matching_pairs("1:C 2:A 3:D 4:B 5:E") == expected

    # Format 4: Comma-separated letters
    assert parse_matching_pairs("C, A, D, B, E") == expected

    # Format 5: JSON string
    assert (
        parse_matching_pairs('{"pairs": {"1": "C", "2": "A", "3": "D", "4": "B", "5": "E"}}')
        == expected
    )

    # Empty / invalid input
    assert parse_matching_pairs("") == {}
    assert parse_matching_pairs("hello world") == {}


def test_synthesize_matching_exercise_hsk1(content_service: ContentService):
    """Test dynamic matching exercise synthesis for HSK 1 concept."""
    ex = content_service.synthesize_matching_exercise("hsk1_c01", count=4)
    assert ex is not None
    assert ex.exercise_type == "matching"
    assert ex.concept_id == "hsk1_c01"

    options = ex.options
    assert isinstance(options, dict)
    assert "left" in options and "right" in options
    assert len(options["left"]) == 4
    assert len(options["right"]) == 4

    # Check left items contain words and pinyin
    assert options["left"][0]["id"] == "1"
    assert "word" in options["left"][0]
    assert "pinyin" in options["left"][0]

    # Check right items contain meanings
    assert options["right"][0]["id"] in ("A", "B", "C", "D")
    assert "meaning" in options["right"][0]

    # Check answer pairs
    pairs = ex.answer["pairs"]
    assert len(pairs) == 4
    assert all(k in ("1", "2", "3", "4") for k in pairs)
    assert all(v in ("A", "B", "C", "D") for v in pairs.values())


def test_synthesize_matching_exercise_multi_level(content_service: ContentService):
    """Test dynamic matching exercise synthesis for higher level concepts."""
    ex = content_service.get_or_synthesize_matching_exercise("hsk2_c01", count=5)
    assert ex is not None
    assert ex.exercise_type == "matching"
    assert len(ex.options["left"]) >= 2


@pytest.mark.asyncio
async def test_grader_fast_path_matching():
    """Test deterministic grading of matching exercises without LLM invocation."""
    grader = GraderComponent()

    exercise = Exercise(
        concept_id="hsk1_c01",
        exercise_type="matching",
        prompt="Match words with meanings",
        target_instruction="Match pairs",
        reference_answers=["1C 2A 3D 4B 5E"],
        options={
            "left": [
                {"id": "1", "word": "你好"},
                {"id": "2", "word": "谢谢"},
                {"id": "3", "word": "再见"},
                {"id": "4", "word": "对不起"},
                {"id": "5", "word": "不客气"},
            ],
            "right": [
                {"id": "A", "meaning": "Thank you"},
                {"id": "B", "meaning": "Sorry"},
                {"id": "C", "meaning": "Hello"},
                {"id": "D", "meaning": "Goodbye"},
                {"id": "E", "meaning": "You're welcome"},
            ],
        },
        metadata={"pairs": {"1": "C", "2": "A", "3": "D", "4": "B", "5": "E"}},
    )

    # 1. Exact 5/5 match
    result_perfect = await grader.grade(exercise, "1C 2A 3D 4B 5E")
    assert result_perfect.passed_gates is True
    assert result_perfect.scores.semantic_precision == 1.0
    assert result_perfect.grader_version == "deterministic-matching"
    assert len(result_perfect.detected_errors) == 0

    # 2. 4/5 match (1 error) -> should still pass (80% threshold)
    result_4_of_5 = await grader.grade(exercise, "1C 2A 3D 4B 5A")
    assert result_4_of_5.passed_gates is True
    assert result_4_of_5.scores.semantic_precision == 0.80

    # 3. 2/5 match -> should fail
    result_fail = await grader.grade(exercise, "1A 2B 3C 4D 5E")
    assert result_fail.passed_gates is False
    assert result_fail.scores.semantic_precision <= 0.40
    assert "ERR_VOCAB_MATCH" in result_fail.detected_errors

    # 4. Invalid formatting
    result_invalid = await grader.grade(exercise, "invalid text")
    assert result_invalid.passed_gates is False
    assert "ERR_FORMAT_MATCHING" in result_invalid.detected_errors


def test_orchestrator_fallback_grade_matching():
    """Test deterministic orchestrator fallback grading for matching exercises."""
    exercise = Exercise(
        concept_id="hsk1_c01",
        exercise_type="matching",
        prompt="Match words",
        target_instruction="Match pairs",
        reference_answers=["1C 2A 3D"],
        options={
            "left": [
                {"id": "1", "word": "A"},
                {"id": "2", "word": "B"},
                {"id": "3", "word": "C"},
            ],
            "right": [
                {"id": "A", "meaning": "B"},
                {"id": "B", "meaning": "C"},
                {"id": "C", "meaning": "A"},
            ],
        },
        metadata={"pairs": {"1": "C", "2": "A", "3": "D"}},
    )

    result = DeterministicOrchestrator._deterministic_fallback_grade(
        exercise,
        "1C 2A 3D",
    )

    assert result.passed_gates is True
    assert result.scores.semantic_precision == 1.0


def test_get_exercises_for_concept_includes_matching(content_service: ContentService):
    """Verify that get_exercises_for_concept automatically prepends a matching exercise."""
    exercises = content_service.get_exercises_for_concept("hsk1_c01", limit=3)
    assert len(exercises) > 0
    assert exercises[0].exercise_type == "matching"
    assert exercises[0].options is not None
    assert "left" in exercises[0].options
    assert "right" in exercises[0].options


def test_matching_exercise_excludes_grammar_structures(content_service: ContentService):
    """Verify that synthesized matching exercises contain strictly vocabulary words and no grammar templates."""
    ex = content_service.synthesize_matching_exercise("hsk1_c03", count=5)
    assert ex is not None
    left_words = [item["word"] for item in ex.options["left"]]
    for w in left_words:
        assert "A" not in w and "B" not in w
        assert "+" not in w and "..." not in w
        assert len(w) <= 8


def test_matching_exercise_meanings_are_english_only(content_service: ContentService):
    """Verify that meanings on the right-hand column are valid English strings and not Hanzi."""
    for concept_id in ("hsk1_c01", "hsk1_c02", "hsk1_c03"):
        ex = content_service.synthesize_matching_exercise(concept_id, count=5)
        if ex and ex.options and "right" in ex.options:
            for item in ex.options["right"]:
                meaning = item["meaning"]
                assert meaning, "Meaning should not be empty"
                # Meaning must have ASCII letters
                assert any(c.isascii() and c.isalpha() for c in meaning), (
                    f"Meaning '{meaning}' should contain English letters"
                )
                # Meaning must not be identical to any Chinese word in the left column
                left_words = [l["word"] for l in ex.options["left"]]
                assert meaning not in left_words, (
                    f"Meaning '{meaning}' should not equal a Chinese word"
                )


def test_planner_progresses_from_current_mastery_to_target_level(content_service: ContentService):
    """Verify that when a learner's goal is set to a higher level milestone,
    the planner continues sequentially from their current unmastered concept
    rather than jumping ahead to the target level.
    """
    from goalcoach.agents.planning_agent import PlanningWorker
    from goalcoach.domain.models import ConceptMastery, LearnerState

    planner = PlanningWorker()
    state = LearnerState(
        learner_id="test_learner_progression",
        goal=LearningGoal(
            title="Target Higher Milestone", target_hsk_level=3, daily_available_minutes=20
        ),
        mastery={
            "hsk1_c01": ConceptMastery(concept_id="hsk1_c01", mastery_score=1.0),
            "hsk1_c02": ConceptMastery(concept_id="hsk1_c02", mastery_score=1.0),
            "hsk1_c03": ConceptMastery(concept_id="hsk1_c03", mastery_score=1.0),
            "hsk1_c04": ConceptMastery(concept_id="hsk1_c04", mastery_score=1.0),
        },
    )

    plan = planner._heuristic_fallback(state, content_service, available_minutes=20)
    assert len(plan.ordered_items) > 0
    # The next sequential unmastered concept must be scheduled
    new_items = [it for it in plan.ordered_items if it.kind == "new"]
    assert len(new_items) > 0
    assert new_items[0].concept_id == "hsk1_c05"


def test_resolve_active_level_unlocks_progressively(content_service: ContentService):
    """Verify that resolve_active_level only unlocks higher levels once current level is mastered."""
    from goalcoach.agents.planning_agent import resolve_active_level
    from goalcoach.domain.models import ConceptMastery, LearnerState

    # 1. Partial HSK 1 mastery -> active level remains HSK 1
    state = LearnerState(
        learner_id="test_active_level",
        goal=LearningGoal(title="HSK 3 Goal", target_hsk_level=3),
        mastery={
            "hsk1_c01": ConceptMastery(concept_id="hsk1_c01", mastery_score=1.0),
            "hsk1_c02": ConceptMastery(concept_id="hsk1_c02", mastery_score=1.0),
        },
    )
    assert resolve_active_level(state, content_service) == 1

    # 2. Complete HSK 1 mastery -> unlocks HSK 2
    hsk1_concepts = content_service.list_all_concepts(hsk_level=1)
    complete_hsk1_mastery = {
        c.concept_id: ConceptMastery(concept_id=c.concept_id, mastery_score=1.0)
        for c in hsk1_concepts
    }
    state.mastery = complete_hsk1_mastery
    assert resolve_active_level(state, content_service) == 2

    # 3. Complete both HSK 1 and HSK 2 mastery -> unlocks target HSK 3
    hsk2_concepts = content_service.list_all_concepts(hsk_level=2)
    complete_hsk2_mastery = {
        c.concept_id: ConceptMastery(concept_id=c.concept_id, mastery_score=1.0)
        for c in hsk2_concepts
    }
    state.mastery = {**complete_hsk1_mastery, **complete_hsk2_mastery}
    assert resolve_active_level(state, content_service) == 3
