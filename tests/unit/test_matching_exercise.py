"""Unit and integration tests for mix-and-match (matching) exercise type,
dynamic synthesis, input format parsing, and deterministic fast-path grading.
"""

from pathlib import Path

import pytest

from goalcoach.agents.grader_component import GraderComponent, parse_matching_pairs
from goalcoach.application.orchestrator import DeterministicOrchestrator
from goalcoach.domain.models import AnswerSubmission, Exercise, LearningGoal
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
    assert parse_matching_pairs('{"pairs": {"1": "C", "2": "A", "3": "D", "4": "B", "5": "E"}}') == expected

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
    assert all(k in ("1", "2", "3", "4") for k in pairs.keys())
    assert all(v in ("A", "B", "C", "D") for v in pairs.values())


def test_synthesize_matching_exercise_hsk2(content_service: ContentService):
    """Test dynamic matching exercise synthesis for HSK 2 concept."""
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
    orchestrator = DeterministicOrchestrator()

    exercise = Exercise(
        concept_id="hsk1_c01",
        exercise_type="matching",
        prompt="Match words",
        target_instruction="Match pairs",
        reference_answers=["1C 2A 3D"],
        options={
            "left": [{"id": "1", "word": "A"}, {"id": "2", "word": "B"}, {"id": "3", "word": "C"}],
            "right": [{"id": "A", "meaning": "B"}, {"id": "B", "meaning": "C"}, {"id": "C", "meaning": "A"}],
        },
        metadata={"pairs": {"1": "C", "2": "A", "3": "D"}},
    )

    result = orchestrator._deterministic_fallback_grade(exercise, "1C 2A 3D")
    assert result.passed_gates is True
    assert result.scores.semantic_precision == 1.0

