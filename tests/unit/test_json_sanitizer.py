"""Unit tests for the LLM JSON output extractor and sanitizer."""

import pytest

from goalcoach.infrastructure.llm.json_sanitizer import extract_and_sanitize_json


def test_sanitize_clean_json() -> None:
    raw = '{"exercise_id": "e1", "passed_gates": true, "scores": {"grammatical_correctness": 1.0}}'
    result = extract_and_sanitize_json(raw)
    assert result["exercise_id"] == "e1"
    assert result["passed_gates"] is True
    assert result["scores"]["grammatical_correctness"] == 1.0


def test_sanitize_markdown_code_block() -> None:
    raw = """
Here is the grading evaluation:
```json
{
  "exercise_id": "e2",
  "scores": {
    "grammatical_correctness": 0.95,
    "semantic_precision": 0.90,
    "pragmatic_appropriateness": 1.0
  },
  "passed_gates": true
}
```
Hope this is helpful!
"""
    result = extract_and_sanitize_json(raw)
    assert result["exercise_id"] == "e2"
    assert result["scores"]["semantic_precision"] == 0.90
    assert result["passed_gates"] is True


def test_sanitize_markdown_code_block_without_json_tag() -> None:
    raw = """
```
{
  "exercise_id": "e3",
  "feedback": "Good job!"
}
```
"""
    result = extract_and_sanitize_json(raw)
    assert result["exercise_id"] == "e3"
    assert result["feedback"] == "Good job!"


def test_sanitize_conversational_prefix_and_suffix() -> None:
    raw = 'Sure! Here is the evaluation:\n{"exercise_id": "e4", "confidence": 0.95}\nPlease review above.'
    result = extract_and_sanitize_json(raw)
    assert result["exercise_id"] == "e4"
    assert result["confidence"] == 0.95


def test_sanitize_nested_stringified_json_fields() -> None:
    # Model serialized nested scores and detected_errors as JSON strings
    raw = (
        '{"exercise_id": "e5", '
        '"scores": "{\\"grammatical_correctness\\": 0.85, \\"semantic_precision\\": 0.80, \\"pragmatic_appropriateness\\": 0.9}", '
        '"detected_errors": "[\\"ERR_WORD_ORDER\\", \\"ERR_SEMANTIC\\"]", '
        '"passed_gates": false}'
    )
    result = extract_and_sanitize_json(raw)
    assert result["exercise_id"] == "e5"
    assert isinstance(result["scores"], dict)
    assert result["scores"]["grammatical_correctness"] == 0.85
    assert isinstance(result["detected_errors"], list)
    assert result["detected_errors"] == ["ERR_WORD_ORDER", "ERR_SEMANTIC"]
    assert result["passed_gates"] is False


def test_sanitize_escaped_quotes_throughout() -> None:
    raw = r"{\"exercise_id\": \"e6\", \"passed_gates\": true, \"scores\": {\"semantic_precision\": 1.0}}"
    result = extract_and_sanitize_json(raw)
    assert result["exercise_id"] == "e6"
    assert result["passed_gates"] is True
    assert result["scores"]["semantic_precision"] == 1.0


def test_sanitize_double_encoded_json_string() -> None:
    raw = '"{\\"exercise_id\\": \\"e7\\", \\"feedback\\": \\"Nice!\\"}"'
    result = extract_and_sanitize_json(raw)
    assert result["exercise_id"] == "e7"
    assert result["feedback"] == "Nice!"


def test_sanitize_empty_or_invalid_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Empty response"):
        extract_and_sanitize_json("")

    with pytest.raises(ValueError):
        extract_and_sanitize_json("I cannot grade this because of an internal error.")

    with pytest.raises(TypeError, match="Expected JSON object"):
        extract_and_sanitize_json('["an", "array"]')
