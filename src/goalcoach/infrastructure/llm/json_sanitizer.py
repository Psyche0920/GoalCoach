"""Robust JSON extractor and sanitizer for heterogeneous LLM outputs.

Handles common LLM idiosyncrasies across different models and inference providers:
- Markdown code fences (```json ... ``` or ``` ... ```)
- Conversational preambles or suffixes (e.g. reasoning, greeting, sign-off)
- Escaped quotes (\\") inside JSON strings or top-level objects
- Double-encoded/stringified nested JSON objects (e.g. "scores": "{\\"...\": ...}")
- Control characters and unescaped newlines in strings
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _maybe_parse_json_str(val: Any) -> Any:
    """If a value is a stringified JSON object or array, parse it recursively."""
    if isinstance(val, str):
        stripped = val.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        ):
            try:
                parsed = json.loads(stripped, strict=False)
                return _unwrap_nested(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
    return val


def _unwrap_nested(data: Any) -> Any:
    """Recursively walks dicts and lists, unwrapping stringified JSON children."""
    if isinstance(data, dict):
        return {k: _unwrap_nested(_maybe_parse_json_str(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [_unwrap_nested(_maybe_parse_json_str(item)) for item in data]
    return data


def extract_and_sanitize_json(raw_text: str) -> dict[str, Any]:
    """Extract and sanitize a JSON object dictionary from arbitrary LLM output text.

    Args:
        raw_text: Raw response string from the language model.

    Returns:
        dict[str, Any]: Parsed and unwrapped JSON dictionary.

    Raises:
        ValueError: If no valid JSON object can be extracted or parsed.
    """
    text = raw_text.strip()
    if not text:
        raise ValueError("Empty response cannot be parsed as JSON")

    # 1. Extract markdown code block if present
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if code_block_match:
        text = code_block_match.group(1).strip()

    # 2. Extract outermost { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
    else:
        candidate = text

    # 3. Attempt JSON parse
    try:
        data = json.loads(candidate, strict=False)
    except json.JSONDecodeError:
        # Fallback: normalize escaped quotes if the model emitted raw escaped JSON
        unescaped = candidate.replace(r"\"", '"')
        try:
            data = json.loads(unescaped, strict=False)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse sanitized JSON: {exc}") from exc

    # 4. Handle double-encoded JSON string (e.g. top-level parsed to a JSON string)
    if isinstance(data, str):
        try:
            data = json.loads(data, strict=False)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Double-encoded string could not be parsed: {exc}") from exc

    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object (dict), got {type(data).__name__}")

    # 5. Recursively unwrap stringified nested fields
    return _unwrap_nested(data)


__all__ = ["extract_and_sanitize_json"]
