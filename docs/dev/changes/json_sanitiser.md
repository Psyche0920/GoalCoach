# Change Log: Heterogeneous LLM JSON Output Sanitizer & Grader Robustness

## 1. Problem Statement

When testing freeform answer grading from the web frontend (`localhost:3000`), approximately 90% of open-ended submissions received no response or failed with the fallback notice:
> *"This answer could not be evaluated by the language model. It was not counted as correct; please retry when model service is available."*

### Root Cause Analysis
1. **Tool Schema Serialization Discrepancy**:
   - `grader_agent` used PydanticAI with `output_type=GradingResult`, which expects a nested object `scores: RubricScores`.
   - Different open-source models (such as `qwen/qwen3.5-9b` hosted via OpenRouter/Venice) often serialize nested dictionary fields inside function call parameters as an **escaped JSON string**:
     ```json
     "scores": "{\"grammatical_correctness\": 1.0, \"semantic_precision\": 0.9, \"pragmatic_appropriateness\": 0.9}"
     ```
     rather than an unquoted nested JSON object.
2. **Pydantic Validation Rejection**:
   - Pydantic strictly rejected this with:
     ```text
     pydantic_core._pydantic_core.ValidationError: 1 validation error for GradingResult
     scores
       Input should be an object [type=model_type, input_type=str]
     ```
3. **Cascading Failure**:
   - PydanticAI retried up to `llm_max_retries=2`, but the model generated the exact same escaped string on each attempt.
   - Retries were exhausted, raising `UnexpectedModelBehavior("Exceeded maximum retries (2) for output validation")`.
   - With local fallback disabled (`GOALCOACH_ENABLE_OLLAMA_FALLBACK=false`), `run_with_fallback` raised `LLMUnavailableError`.
   - `grader_component.py` caught `LLMUnavailableError` and triggered `_deterministic_fallback(...)`.
4. **Why 90%**:
   - Deterministic fast-path evaluation handles exact reference matches and matching exercises (<1ms, ~10% of submissions).
   - All natural, freeform variations (~90%) routed through the LLM and failed validation.
5. **Secondary Issues**:
   - Unreachable dead code at lines 346–349 of `grader_component.py`.
   - `TeachingCard` had an invalid `audio_url` attribute access in `teaching_agent.py` (line 131), throwing `AttributeError`.
   - Legacy `_attach_curriculum_exercise` helper method remained in `TeachingWorker`.

---

## 2. Solution & Architectural Design

Instead of relying on fragile provider-dependent tool-calling serialization:
1. **Dedicated JSON Sanitizer Engine (`extract_and_sanitize_json`)**:
   - Extracts JSON from markdown fences (` ```json ... ``` ` or ` ``` ... ``` `) using regex.
   - Finds outermost `{ ... }` boundaries to ignore conversational preambles/reasoning tokens and suffixes.
   - Normalizes escaped quotes (`\"`).
   - Handles double-encoded JSON strings.
   - Recursively traverses dictionaries and lists to unwrap any stringified nested JSON structures into true Python `dict`/`list` objects.
2. **Raw JSON String Agent Output**:
   - Configured `grader_agent` with `output_type=str` and structured the prompt to strictly request a standard JSON object.
   - Passed output through `extract_and_sanitize_json(...)` before validating into `GradingResult`.
   - Added bounded retries with feedback on validation failure.
3. **Cleaned Legacy and Non-Existent Attributes**:
   - Removed `audio_url` reference from `teaching_agent.py`.
   - Removed legacy `TeachingWorker._attach_curriculum_exercise` and updated relevant integration tests to use the active candidate exercise selection and attachment pipeline.

---

## 3. Target Files & Changed Lines

### File 1: `src/goalcoach/infrastructure/llm/json_sanitizer.py` (New File)
- **Status**: Created (102 lines).
- **Function**: `extract_and_sanitize_json(raw_text: str) -> dict[str, Any]`
- **Key Logic**:
  - Regex extraction of code blocks: `re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)`
  - Outermost `{ ... }` slicing.
  - Escaped quote unescaping fallback.
  - Recursive `_unwrap_nested` and `_maybe_parse_json_str` for stringified inner JSON structures.

---

### File 2: `src/goalcoach/agents/grader_component.py`
- **Target Lines**:
  - Line 28: Imported `extract_and_sanitize_json`.
  - Lines 60–85: Updated `GRADER_SYSTEM_PROMPT` with strict JSON schema instructions; changed `grader_agent` `output_type=str`.
  - Lines 295–365: Replaced direct tool invocation with bounded retry loop using `extract_and_sanitize_json` and `GradingResult.model_validate(data)`.
  - Lines 346–349 (former): Removed unreachable dead code.

#### Key Code Diff:
```python
# Before:
grader_agent = Agent(
    model=get_openrouter_model(),
    output_type=GradingResult,
    output_retries=get_output_retries(),
    system_prompt=GRADER_SYSTEM_PROMPT,
)
...
try:
    result, provider = await run_with_fallback(self.agent, prompt, deps=None, component="grader_component")
    llm_result: GradingResult = result.output
    ...
except LLMUnavailableError as exc:
    return self._deterministic_fallback(...)
return self._deterministic_fallback(...)  # UNREACHABLE DEAD CODE

# After:
grader_agent = Agent(
    model=get_openrouter_model(),
    output_type=str,
    output_retries=get_output_retries(),
    system_prompt=GRADER_SYSTEM_PROMPT,
)
...
max_validation_retries = get_output_retries()
current_prompt = prompt
llm_result: GradingResult | None = None
last_error: Exception | None = None
provider = "unknown"

for attempt in range(max_validation_retries + 1):
    try:
        result, provider = await run_with_fallback(
            self.agent,
            current_prompt,
            deps=None,
            component="grader_component",
        )
        if isinstance(result.output, GradingResult):
            llm_result = result.output
        else:
            data = extract_and_sanitize_json(str(result.output))
            data.setdefault("exercise_id", exercise_id)
            llm_result = GradingResult.model_validate(data)
        break
    except LLMUnavailableError as exc:
        return self._deterministic_fallback(
            exercise_id,
            notice=f"LLM unavailable; conservative deterministic grading fallback used: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        last_error = exc
        logger.warning(
            "Grader output validation attempt %d/%d failed (%s); retrying...",
            attempt + 1,
            max_validation_retries + 1,
            exc,
        )
        current_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Your previous response was invalid: {exc}. "
            "You must output ONLY a valid JSON object matching the requested schema."
        )

if llm_result is None:
    return self._deterministic_fallback(
        exercise_id,
        notice=f"Grader returned an invalid rubric result; deterministic fallback used: {last_error}",
    )
```

---

### File 3: `src/goalcoach/agents/teaching_agent.py`
- **Target Lines**:
  - Line 131: Removed `"audio_url": card.audio_url,` from `get_concept_teaching_cards` dictionary comprehension.
  - Lines 363–380: Removed legacy static method `_attach_curriculum_exercise`.

#### Key Code Diff:
```python
# Before:
        {
            "card_id": card.card_id,
            "concept_id": card.concept_id,
            "prompt_zh": card.prompt_zh,
            "pinyin": card.pinyin,
            "meaning_en": card.meaning_en,
            "example_zh": card.example_zh,
            "example_pinyin": card.example_pinyin,
            "example_en": card.example_en,
            "explanation_en": card.explanation_en,
            "audio_url": card.audio_url,
        }

# After:
        {
            "card_id": card.card_id,
            "concept_id": card.concept_id,
            "prompt_zh": card.prompt_zh,
            "pinyin": card.pinyin,
            "meaning_en": card.meaning_en,
            "example_zh": card.example_zh,
            "example_pinyin": card.example_pinyin,
            "example_en": card.example_en,
            "explanation_en": card.explanation_en,
        }
```

---

### File 4: `tests/integration/test_remediation_loop.py`
- **Target Lines**:
  - Lines 136–143: Replaced call to deleted `_attach_curriculum_exercise` with active workflow methods `_select_candidate_exercise` and `_attach_selected_exercise`.

#### Key Code Diff:
```python
# Before:
    replaced = TeachingWorker._attach_curriculum_exercise(
        action,
        content_service,
        state=LearnerState(),
        is_remedial=True,
        excluded_exercise_id="hsk1_c01_e01",
    )

# After:
    selected = TeachingWorker._select_candidate_exercise(
        action.concept_id,
        content_service,
        state=LearnerState(),
        is_remedial=True,
        excluded_exercise_id="hsk1_c01_e01",
    )
    replaced = TeachingWorker._attach_selected_exercise(action, selected)
```

---

### File 5: `tests/unit/test_json_sanitizer.py` (New File)
- **Status**: Created (84 lines).
- **Test Cases**:
  - `test_sanitize_clean_json`
  - `test_sanitize_markdown_code_block`
  - `test_sanitize_markdown_code_block_without_json_tag`
  - `test_sanitize_conversational_prefix_and_suffix`
  - `test_sanitize_nested_stringified_json_fields`
  - `test_sanitize_escaped_quotes_throughout`
  - `test_sanitize_double_encoded_json_string`
  - `test_sanitize_empty_or_invalid_raises_value_error`

---

## 4. Verification & Testing Evidence

1. **Unit & Integration Test Suite**:
   ```bash
   .venv/bin/pytest
   # Result: 147 passed, 5 warnings in 1.23s
   ```
2. **Linting & Code Standards**:
   ```bash
   .venv/bin/ruff check src/ tests/
   # Result: All checks passed!
   ```
3. **Live LLM Model Grading (OpenRouter `qwen/qwen3.5-9b`)**:
   - Submission: `"我想吃一个苹果"` for prompt *"Translate 'I want to eat apples' into Chinese"*.
   - Result: Correctly parsed, evaluated, and validated on first attempt without schema error.
   - Outcome: `passed_gates=True`, `grammatical_correctness=1.0`, `semantic_precision=0.9`, personalized natural feedback.
4. **Backend Server Service**:
   - HTTP GET `/health` returned `200 OK` (`{"status":"ok"}`).
