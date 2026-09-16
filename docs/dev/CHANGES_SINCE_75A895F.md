# Coding Changes Since the Last Push

## Baseline and Scope

This document describes the local, uncommitted coding changes made after the last pushed commit:

```text
75a895f fix(grader): harden critical error prefix matching in gating guardrails
```

The local branch and `origin/feature/teaching-agent-demo` both point to `75a895f`. The changes documented here address two defects found while manually testing the terminal learning loop:

1. OpenRouter structured-output failures incorrectly triggered an unconditional local Ollama attempt.
2. The terminal used a fabricated exercise ID and could treat the learner's answer as its own reference answer, producing an incorrect deterministic score of `1.0`.

SQLite `-wal` and `-shm` runtime files are not part of these coding changes and should not be committed.

## Change Summary

```text
10 tracked files changed
118 insertions
19 deletions
```

Modified areas:

- LLM configuration and OpenRouter client construction
- Structured-output validation retries
- Optional Ollama fallback behavior
- Teaching Agent exercise grounding
- Terminal exercise display and submission
- Orchestrator grading safety
- Integration and regression tests

## 1. OpenRouter and Model Fallback Handling

### Previous behavior

The model wrapper caught nearly every failure because its exception clause included `Exception`:

```python
except (httpx.HTTPError, httpx.TimeoutException, Exception):
```

It then always attempted the configured Ollama endpoint. This happened even when:

- Ollama was not installed;
- no local model had been downloaded;
- the primary failure was an output-validation error rather than a network failure.

The resulting sequence was:

```text
OpenRouter returns an invalid structured response
    -> PydanticAI exhausts output validation retries
    -> application attempts localhost:11434
    -> Ollama connection fails
    -> worker uses its deterministic heuristic
```

Although `.env` exposed timeout and retry settings, those settings were not connected to the HTTP client or the Agents. PydanticAI therefore used its default structured-output retry count.

### New behavior

#### Optional Ollama fallback

`Settings` now includes:

```python
enable_ollama_fallback: bool = False
```

The corresponding example configuration is:

```dotenv
GOALCOACH_ENABLE_OLLAMA_FALLBACK=false
```

Ollama is no longer contacted unless the fallback is explicitly enabled.

#### Effective HTTP timeout

The configured timeout is now passed to an `httpx.AsyncClient` used by `OpenAIProvider`:

```python
http_client = httpx.AsyncClient(timeout=settings.llm_timeout_seconds)
provider = OpenAIProvider(
    base_url=base_url,
    api_key=api_key,
    http_client=http_client,
)
```

This applies to both the OpenRouter model and the optional Ollama model.

#### Narrower error classification

`run_with_fallback()` now handles the relevant model-boundary failures explicitly:

```python
except (httpx.HTTPError, ModelAPIError, UnexpectedModelBehavior) as err:
```

It distinguishes:

- `output validation` failures, represented by `UnexpectedModelBehavior`;
- `connection or provider` failures, represented by HTTP or model API errors.

When Ollama fallback is disabled, the error is re-raised to the calling worker. The worker then applies its existing deterministic fallback without first waiting for an unavailable local model.

#### Effective structured-output retries

The model module now exposes:

```python
def get_output_retries() -> int:
    return Settings().llm_max_retries
```

The following Agents now pass that value through `output_retries`:

- `planning_agent`
- `teaching_agent`
- legacy `tutor_agent`
- `grader_agent` in `grader_component.py`

With this configuration:

```dotenv
GOALCOACH_LLM_MAX_RETRIES=2
```

PydanticAI gets additional opportunities to ask the model to correct output that does not satisfy `PlanUpdate`, `TeachingAction`, `TutorResponse`, or `GradingResult`.

### Files changed

- `.env.example`
- `src/goalcoach/infrastructure/config.py`
- `src/goalcoach/infrastructure/llm/pydantic_ai_models.py`
- `src/goalcoach/agents/planning_agent.py`
- `src/goalcoach/agents/teaching_agent.py`
- `src/goalcoach/agents/grader_component.py`

## 2. Terminal Grading and Canonical Exercises

### Previous behavior

The terminal submitted a generated exercise ID:

```python
exercise_id = f"{concept_id}_practice"
```

IDs such as `hsk1_c01_practice` do not exist in the curriculum database. When the orchestrator could not find the exercise, it created a synthetic exercise with:

```python
reference_answers=[answer]
```

This made the learner's submitted answer equal to the newly created reference answer. The Grader's exact-match fast path therefore returned:

```text
passed_gates = true
grammatical_correctness = 1.0
semantic_precision = 1.0
pragmatic_appropriateness = 1.0
grader_version = deterministic-fast-path
```

This was a correctness and data-integrity defect. It also prevented meaningful testing of the OpenRouter Grader from the terminal.

### New behavior

#### Teaching actions are grounded in the curriculum database

`TeachingWorker` now calls:

```python
content_service.get_exercises_for_concept(
    action.concept_id,
    limit=1,
    randomize=False,
)
```

The selected exercise is attached to `TeachingAction.exercise_payload`:

```json
{
  "exercise_id": "hsk1_c01_e01",
  "concept_id": "hsk1_c01",
  "prompt": "你好",
  "instruction": "Choose the meaning."
}
```

Reference and accepted answers remain server-side and are not exposed to the learner.

Both LLM-generated teaching actions and deterministic heuristic actions are enriched with a canonical exercise. If a curriculum concept has no exercise, the worker raises `LookupError` instead of creating ungrounded assessment data.

#### Terminal displays and submits the real exercise

The terminal now renders a separate `Practice` panel containing the database instruction and prompt.

It submits:

```python
"exercise_id": str(exercise_payload["exercise_id"])
```

If a teaching action has no exercise payload, the terminal fails immediately with a clear runtime error.

#### Unknown exercise IDs are rejected

The orchestrator no longer creates a synthetic exercise from the learner's answer. It now raises:

```text
Unknown exercise_id '...'; answers can only be graded against canonical curriculum exercises
```

Consequently:

- an exact database answer can still use the intended deterministic fast path;
- a non-exact answer can be evaluated by the OpenRouter Grader;
- an unknown exercise cannot silently become correct.

### Files changed

- `src/goalcoach/agents/teaching_agent.py`
- `src/goalcoach/agents/terminal_harness.py`
- `src/goalcoach/application/orchestrator.py`

## 3. Test Changes

### Ollama fallback test

The existing failover integration test now explicitly enables Ollama fallback:

```python
monkeypatch.setenv("GOALCOACH_ENABLE_OLLAMA_FALLBACK", "true")
```

This preserves coverage of the optional OpenRouter-to-Ollama path while keeping production and normal development behavior disabled by default.

### Canonical exercise assertions

The closed-loop teaching test now verifies that both the initial explanation and adapted teaching action contain the real exercise:

```text
hsk1_c04_e01
```

### Unknown exercise regression test

A new regression test submits:

```text
exercise_id = hsk1_c01_practice
answer = xyz
```

It asserts that the orchestrator raises `ValueError` instead of treating `xyz` as the reference answer.

### Files changed

- `tests/integration/test_pydantic_ai_pipeline.py`
- `tests/integration/test_closed_loop.py`

## 4. Verification Performed

### Automated tests

The following combined suite passed:

```bash
GOALCOACH_ENVIRONMENT=testing \
GOALCOACH_LLM_API_KEY=ci-mock-token \
.venv/bin/python -m pytest \
  tests/integration/test_closed_loop.py \
  tests/unit \
  tests/api \
  -q
```

Result:

```text
83 passed
```

The focused model failover tests also passed:

```text
2 passed
```

### OpenRouter connectivity

The configured OpenRouter endpoint and model were tested directly:

```text
Endpoint: https://openrouter.ai/api/v1/chat/completions
Model: qwen/qwen-2.5-72b-instruct
HTTP status: 200
Response: OK
```

A standalone structured `TeachingAction` request also succeeded.

### End-to-end terminal verification

The terminal was run against an isolated temporary learner database while using the configured OpenRouter model.

Displayed exercise:

```text
Instruction: Choose the meaning.
Prompt: 你好
```

Submitted answer:

```text
Goodbye
```

Observed result:

```text
Status: FAIL
Grammar: 0.00
Semantic: 0.00
Detected Errors: ['ERR_VOCABULARY']
Grader Version: v1.0.0
```

`v1.0.0` confirms that this non-exact answer was evaluated by the OpenRouter Grader rather than the deterministic exact-match path or heuristic fallback.

## 5. Intentionally Unresolved Issues

These changes do not yet solve the following learning-loop concerns:

- `SESSION_STARTED` still passes `failed_attempts=0`, so ordinary failed-answer history is not yet propagated into Teaching Agent strategy selection.
- Remediation has no explicit terminal condition based on consecutive correct answers or sufficient evidence.
- Exercise selection currently uses the first exercise with `randomize=False`; exercise rotation and attempt history are still required.
- Mastery still changes by fixed increments (`+0.25` on pass and `-0.10` on failure) rather than being derived from rubric evidence.
- The Planner still needs stronger deterministic filtering to prevent already-mastered concepts from being scheduled incorrectly.
- The terminal focus title still exposes internal IDs such as `hsk1_c01` instead of only displaying the curriculum title.

These should be addressed separately so the model-transport and grading-integrity fixes remain reviewable and testable.

## 6. Recommended Commit Split

For a clean review history, the current work can be split into two commits:

```text
fix(llm): apply output retries and make Ollama fallback opt-in
fix(terminal): grade canonical curriculum exercises instead of synthetic answers
```

The generated SQLite `-wal` and `-shm` files should remain untracked and excluded from both commits.
