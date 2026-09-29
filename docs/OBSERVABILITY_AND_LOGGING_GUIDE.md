# GoalCoach Enterprise Observability & Structured Logging Guide

This guide explains how to test the GoalCoach observability and structured logging system, where to find specific log streams, and how to interpret each telemetry event.

---

## 1. How to Test the Logging System

### Option A: Interactive Terminal Study Harness
The CLI harness supports two logging modes:

1. **Live Development Log Stream (Console)**:
   ```bash
   uv run goalcoach --verbose
   ```
   *Runs the interactive terminal study loop and prints real-time ANSI-colorized logs to your console alongside the interactive UI.*

2. **Clean Interactive UI (Logs to File)**:
   ```bash
   uv run goalcoach
   ```
   *Keeps the terminal UI clean without log clutter. All structured NDJSON logs are automatically appended to `./logs/goalcoach.log` in the background.*

---

### Option B: FastAPI Backend Server
1. **Start the API server**:
   ```bash
   uv run uvicorn apps.api.main:app --port 8000
   ```
   *On server start, the application lifespan initializes the structured logging system according to typed environment settings.*

2. **Send a request**:
   ```bash
   curl -i http://localhost:8000/health
   ```
   **Response Headers**:
   ```http
   HTTP/1.1 200 OK
   x-request-id: 9a5b3f2e1c8d4e0a9b2c3d4e5f6a7b8c
   x-response-time-ms: 1.15
   ```
   **Console Output**:
   ```text
   [15:55:01.234] [INFO   ] [apps.api.access] HTTP GET /health 200 (1.15ms) [request_id=9a5b3f2e1c8d4e0a9b2c3d4e5f6a7b8c]
   ```

---

### Option C: Automated Unit & Performance Tests
Run the dedicated test suite to verify context isolation across coroutines, NDJSON formatting, secret scrubbing, and sub-millisecond execution:
```bash
uv run pytest tests/unit/test_observability.py -v
```

---

## 2. Where to Find the Logs

| Destination | Mode / Environment | Description |
| :--- | :--- | :--- |
| **Console (`stdout`)** | Dev / `--verbose` / `uvicorn` | Human-readable colorized output: `[TIME] [LEVEL] [logger] message [context]`. |
| **`./logs/goalcoach.log`** | CLI / File logging | High-speed, machine-readable **NDJSON** (1 JSON object per line). Automatically rotates at 10 MB with 5 backups. |

To inspect or stream the log file live in another terminal window:
```bash
tail -f ./logs/goalcoach.log
```

---

## 3. How to Read and Understand the Logs

Every log event contains core correlation metadata:
- `timestamp`: UTC timestamp with microsecond accuracy.
- `logger`: The specific module emitting the event.
- `context`: Active request identifiers (`request_id`, `trace_id`, `learner_id`, `concept_id`).
- `extra`: Quantitative performance measurements and business telemetry.

Below are the 6 primary categories of logs:

---

### A. HTTP Request & Access Telemetry
*Emitted by `apps.api.middleware.observability` (`apps.api.access`)*

```json
{
  "timestamp": "2026-09-28T13:50:01.123456Z",
  "level": "INFO",
  "logger": "apps.api.access",
  "message": "HTTP POST /api/v1/events 200 (12.45ms)",
  "context": {
    "request_id": "req-98fa71b2",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
  },
  "extra": {
    "http.method": "POST",
    "http.route": "/api/v1/events",
    "http.status_code": 200,
    "duration_ms": 12.45,
    "client_ip": "127.0.0.1"
  }
}
```
* **What it tells you**: The exact inbound HTTP path, HTTP status code, roundtrip duration in milliseconds, and correlation identifiers.

---

### B. Deterministic Orchestrator State Routing
*Emitted by `goalcoach.application.orchestrator`*

```text
[INFO] [goalcoach.application.orchestrator] Event ANSWER_SUBMITTED received for learner learner_001
[INFO] [goalcoach.application.orchestrator] Event ANSWER_SUBMITTED resolved -> next_action: teach (replanned=False, 84us)
```
* **What it tells you**:
  - `next_action`: What the client is instructed to do next (`teach`, `plan`, `complete`, etc.).
  - `routing_latency_us`: The deterministic decision speed in **microseconds** (typically $<150\,\mu\text{s}$).
  - `replanned`: Whether an adaptive replan occurred during this event.

---

### C. Bayesian DSR Spaced Repetition & Progress Mutations
*Emitted by `goalcoach.application.progress_service`*

```json
{
  "timestamp": "2026-09-28T13:50:02.102938Z",
  "level": "INFO",
  "logger": "goalcoach.application.progress_service",
  "message": "Progress state mutated for concept hsk1_c01 (mastery: 0.40 -> 0.65, R: 1.00, S: 1.8d)",
  "context": { "learner_id": "learner_001", "concept_id": "hsk1_c01" },
  "extra": {
    "event": "progress_state_mutated",
    "concept_id": "hsk1_c01",
    "prior_mastery": 0.40,
    "new_mastery": 0.65,
    "prior_retention": 0.94,
    "retention_r": 1.0,
    "prior_interval_days": 1.0,
    "stability_s": 1.8,
    "quality": 1.0,
    "passed_gates": true,
    "next_review_days": 1.8,
    "needs_replanning_toggled": false
  }
}
```
* **What it tells you**:
  - `mastery`: The psychometric proficiency score ($0.0 \to 1.0$).
  - `retention_r`: The student's estimated memory recall probability ($R$).
  - `stability_s`: The memory half-life/interval in days ($S$). Correct answers expand stability (e.g., $1.0\text{d} \to 1.8\text{d}$).
  - `quality`: The average composite rubric score across grammar, semantics, and pragmatics.

> [!NOTE]
> If a student struggles repeatedly on a concept, you will see a `WARN` event:
> ```text
> [WARN] Remediation threshold exceeded for concept hsk1_c01 (counter: 2); set needs_replanning=True
> ```
> This indicates that the orchestrator will automatically schedule a remedial intervention on the next turn.

---

### D. Grader Component Telemetry (Fast-Path vs. LLM Rubric)
*Emitted by `goalcoach.agents.grader_component`*

**1. Deterministic Fast-Path Evaluation ($<0.05\text{ ms}$)**:
```json
{
  "level": "INFO",
  "message": "Grader resolved via deterministic-fast-path for exercise hsk1_c01_e01 (0.02ms)",
  "extra": {
    "eval_path": "fast_path",
    "exercise_id": "hsk1_c01_e01",
    "passed_gates": true,
    "latency_ms": 0.023,
    "grader_version": "deterministic-fast-path"
  }
}
```
* Bypasses the LLM entirely for exact matches and multiple-choice options, evaluating in fractions of a millisecond.

**2. Probabilistic LLM Rubric Evaluation**:
```json
{
  "level": "INFO",
  "message": "Grader evaluated via LLM rubric for exercise hsk1_c01_e02 (passed=false, 642.31ms)",
  "extra": {
    "eval_path": "llm_rubric",
    "provider": "openrouter:qwen/qwen-2.5-72b-instruct",
    "passed_gates": false,
    "rubric_scores": {
      "grammatical_correctness": 0.5,
      "semantic_precision": 0.4,
      "pragmatic_appropriateness": 0.8
    },
    "detected_errors": ["ERR_QUESTION_MA"],
    "confidence": 0.95,
    "latency_ms": 642.31
  }
}
```
* Shows the 3 rubric axes and taxonomy error tags (e.g. `ERR_QUESTION_MA` for question particle mistakes).

---

### E. SQLite Engine Profiling & Slow Queries ($>25\text{ ms}$)
*Emitted by `goalcoach.persistence.database`*

- **Normal query** (`DEBUG`):
  ```text
  [DEBUG] [goalcoach.persistence.database] SQLite query on content (SELECT, 0.45ms)
  ```
- **Slow query alert** (`WARN`):
  ```text
  [WARN ] [goalcoach.persistence.database] Slow SQLite query on learner_state (UPDATE, 29.80ms): UPDATE learner_states SET state_json = ...
  ```
* Pinpoints write lock wait times or unindexed queries on either the content or learner database.

---

### F. Security & Sanitization
*Enforced by `SecretScrubbingFilter` in `goalcoach.infrastructure.logging.filters`*

Whenever an API token, bearer header, or credential is passed into a log message or query context, it is automatically sanitized:
```text
Original: "Connecting to OpenRouter with key sk-or-v1-abcdef1234567890"
Scrubbed in Log: "Connecting to OpenRouter with key ***REDACTED***"
```
