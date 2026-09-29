# Enterprise Observability & Structured Logging Architecture: GoalCoach Core

This architectural blueprint establishes an end-to-end, asynchronous, structured observability and telemetry layer for the GoalCoach platform. By treating operational metrics, database transactions, deterministic state transitions, and probabilistic agent reasoning as structured event streams, this design ensures that every runtime decision can be measured, debugged, and optimized without introducing blocking latency into fast-path interactions.

---

## 1. Architectural Philosophy & Guiding Invariants

To maintain sub-second responsiveness while providing enterprise-grade auditability across a hybrid deterministic/agentic system, the logging layer must adhere to five non-negotiable invariants:

1. **Non-Blocking Asynchronous Execution:** Fast-path operations (e.g., deterministic multiple-choice question [MCQ] or exact-match grading executing in $<1\text{ ms}$) must never be bottlenecked by logging I/O. Log formatting and write flushes must introduce $<0.05\text{ ms}$ overhead.


2. **Context Propagation via `contextvars`:** State tracking must not pollute domain method signatures. Core identifiers—`request_id`, `trace_id`, `learner_id`, `session_id`, and `concept_id`—must be bound to execution context variables at the system edge (FastAPI ASGI middleware or CLI harness) and automatically injected into all downstream log records.


3. **Structured Machine-Readable Output (NDJSON):** All production and testing logs must be emitted as single-line JSON (Newline Delimited JSON). Local development environments may toggle to colorized, human-readable console rendering.


4. **Strict Sanitization & Zero PII/Secret Leakage:** Model API tokens, database connection credentials, and raw authentication headers must be scrubbed by regex/key filters before serialization.


5. **OpenTelemetry Semantic Convention Alignment:** Attribute naming must conform to OpenTelemetry specifications (`gen_ai.system`, `gen_ai.request.model`, `db.system`, `http.status_code`, `http.route`) to ensure forward compatibility with APM collectors (Datadog, Grafana Loki, OpenTelemetry Collector).



---

## 2. Telemetry & Measurement Matrix

| System Boundary | Measurable Target | Log Level | Emitted Attributes | Architectural Rationale |
| --- | --- | --- | --- | --- |
| **HTTP Gateway (`apps/api`)**<br> | Inbound request, status, roundtrip latency | `INFO` / `WARN` | `http.method`, `http.route`, `http.status_code`, `duration_ms`, `request_id`, `client_ip`<br> | Establishes API latency baselines ($p50, p95, p99$), isolates network bottlenecks, tracks endpoint usage.|
| **Deterministic Orchestrator (`application/orchestrator.py`)**<br> | Event routing, condition matching, next-action resolution | `INFO` | `event_type`, `review_due`, `plan_status`, `needs_replanning`, `action_chosen`, `routing_latency_us`<br> | Verifies core PRD invariant: *Same goal + different state $\rightarrow$ different plan*. Detects routing failures.|
| **Dual SQLite Persistence (`infrastructure/persistence`)**<br> | Query execution, WAL write locks, slow queries ($>25\text{ ms}$) | `DEBUG` / `WARN` | `db.name` (`content` vs `state`), `statement_type`, `duration_ms`, `row_count`, `lock_wait_ms`<br> | Detects transaction lock contention in SQLite WAL mode; pinpoints unindexed content queries.|
| **Progress Engine & Spaced Repetition (`application/progress_service.py`)**<br> | Mathematical state mutations, DSR updates, retention decay | `INFO` | `concept_id`, `prior_mastery`, `new_mastery`, `stability_s`, `decay_r`, `delta_days`, `next_review_at`<br> | Validates psychometric learning formulas, spaced review intervals, and retention decay math.|
| **Grader Component (`agents/grader_component.py`)**<br> | Fast-path deterministic match vs. LLM rubric evaluation | `INFO` | `eval_path` (`fast_path` | `llm_rubric`), `passed_gates`, `rubric_scores`, `error_code`, `latency_ms`<br> | Measures fast-path coverage ratio, catches regex misses, tracks recurrence of misconceptions.|
| **Reasoning Agents (`PlanningWorker`, `TeachingWorker`)**<br> | Prompt version, tool calls, token usage, strategy selection | `INFO` / `DEBUG` | `agent_name`, `action_kind`, `tool_name`, `tool_duration_ms`, `prompt_tokens`, `completion_tokens`<br> | Monitors token economics, tracks context size, optimizes pedagogical strategy selection.|
| **Model Gateway (`infrastructure/llm`)**<br> | Provider dispatches, HTTP timeouts, local failover triggers | `INFO` / `WARN` | `provider` (`openrouter` | `ollama`), `model`, `ttft_ms`, `total_latency_ms`, `error_type`, `fallback_active`<br> | Monitors hosted SLA, measures fallback frequency to local quantized weights, ensures fault tolerance.|

---

## 3. Target File Topology

```text
src/goalcoach/
├── infrastructure/
│   ├── logging/                                 <-- NEW: Core observability module
│   │   ├── __init__.py                          # Public interface: configure_logging, get_logger
│   │   ├── context.py                           # ContextVar propagation (trace_id, learner_id, etc.)
│   │   ├── formatters.py                        # NDJSON production & colorized console dev formatters
│   │   ├── filters.py                           # Secret scrubbing & PII masking
│   │   └── config.py                            # DictConfig builder integrating standard library & OTel
│   ├── persistence/
│   │   └── database.py                          <-- MODIFIED: SQLAlchemy engine event listeners for SQLite
│   └── llm/
│       └── pydantic_ai_models.py                <-- MODIFIED: LLM execution telemetry & failover hooks
├── application/
│   ├── orchestrator.py                          <-- MODIFIED: Decision route & condition logging
│   └── progress_service.py                      <-- MODIFIED: State-diff mathematical transition logging
└── agents/
    ├── grader_component.py                      <-- MODIFIED: Dual-path grading metrics & score capture
    ├── planning_agent.py                        <-- MODIFIED: Budget allocation & tool call tracking
    └── teaching_agent.py                        <-- MODIFIED: Pedagogy strategy selection & card injection
apps/
└── api/
    ├── middleware/
    │   └── observability.py                     <-- NEW: ASGI Correlation & Request Timing Middleware
    └── main.py                                  <-- MODIFIED: Mount middleware & initialize logging lifecycle
tests/
└── unit/
    └── test_observability.py                    <-- NEW: Contract assertions for telemetry & propagation

```

---

## 4. Phased Implementation Roadmap

### Phase 1: Core Logging Engine & Context Propagation

* **Goal:** Establish the foundational structured logging module using Python's standard library `logging` enhanced with context propagation. Avoid heavyweight third-party dependencies by leveraging existing `opentelemetry-api` and `opentelemetry-sdk` dependencies in `pyproject.toml`.


* **Deliverables:**
1. `src/goalcoach/infrastructure/logging/context.py`:
* Define `ContextVar` instances: `ctx_trace_id`, `ctx_request_id`, `ctx_learner_id`, `ctx_session_id`.
* Implement `bind_context(**kwargs)` and `clear_context()`.
* Implement `get_context() -> dict[str, Any]` to safely dump populated values.


2. `src/goalcoach/infrastructure/logging/filters.py`:
* `SecretScrubbingFilter(logging.Filter)`: Inspects `record.msg` and `record.args`. Uses regex matching against patterns (`sk-...`, `Bearer ...`, `password`, `key`) and replaces matches with `***REDACTED***`.
* `ContextInjectionFilter(logging.Filter)`: Pulls active context variables and binds them directly onto `record` attributes (`record.trace_id`, `record.learner_id`, etc.).


3. `src/goalcoach/infrastructure/logging/formatters.py`:
* `JSONFormatter(logging.Formatter)`: Emits a single-line JSON document containing:
* `timestamp` (ISO 8601 UTC with microsecond precision).
* `level` (`INFO`, `WARN`, `ERROR`, `DEBUG`).
* `logger` (e.g., `goalcoach.application.orchestrator`).
* `message` (formatted string).
* `context` (nested object containing `trace_id`, `request_id`, `learner_id`).
* `extra` (arbitrary structured telemetry attributes passed in `logger.info("...", extra={...})`).
* `exception` (sanitized traceback if `exc_info` is present).


* `DevelopmentFormatter(logging.Formatter)`: Emits compact, color-coded terminal text: `[12:34:56.789] [INFO] [orchestrator] Event ANSWER_SUBMITTED -> route: TEACH [learner=abc-123]`.


4. `src/goalcoach/infrastructure/logging/config.py`:
* Build an idempotent `setup_logging(environment: str, level: str)` function.
* Configure loggers: `goalcoach`, `apps.api`, `sqlalchemy.engine`, and `uvicorn.access`.





### Phase 2: HTTP Gateway & ASGI Observability Middleware

* **Goal:** Intercept every inbound HTTP request to the FastAPI application, inject trace identifiers, measure roundtrip duration, and log access details cleanly.


* **Deliverables:**
1. `apps/api/middleware/observability.py`:
* Create `ObservabilityMiddleware(BaseHTTPMiddleware)`.
* Extract incoming `X-Request-ID` or generate `uuid4().hex`.
* Extract W3C `traceparent` or generate a random 128-bit hex `trace_id`.
* Bind IDs via `bind_context(request_id=..., trace_id=...)`.
* Record start time using `time.perf_counter()`.
* Execute downstream handler.
* Calculate `latency_ms = (time.perf_counter() - start) * 1000`.
* Log completion at `INFO` level with `http.method`, `http.route`, `http.status_code`, and `duration_ms`.
* Attach `X-Request-ID` and `X-Response-Time-Ms` to outbound response headers.


2. `apps/api/main.py`:
* Initialize logging in FastAPI `lifespan` handler.
* Mount `ObservabilityMiddleware` as the outermost middleware layer.





### Phase 3: Dual SQLite Persistence Tier & Engine Profiling

* **Goal:** Gain complete visibility into SQLite transaction overhead, query execution durations, and WAL-mode lock contention.


* **Deliverables:**
1. `src/goalcoach/infrastructure/persistence/database.py`:
* Attach SQLAlchemy Core event listeners to the engine:
```python
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.perf_counter()

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    duration_ms = (time.perf_counter() - context._query_start_time) * 1000
    # Identify database target (content vs state) from connection URL
    # If duration > 25.0ms: emit WARN ('db_slow_query')
    # Else: emit DEBUG ('db_query_executed')

```


* Track SQLite lock wait times: Measure duration when executing write transactions against `goalcoach.db` under WAL mode.


* Log database errors (`handle_error` event listener) with SQL dialect details and sanitized statement parameters.







### Phase 4: Deterministic Decision Engine & State Machine Telemetry

* **Goal:** Instrument the closed-loop state machine (`orchestrator.py`) and mathematical learning engine (`progress_service.py`).


* **Deliverables:**
1. `src/goalcoach/application/orchestrator.py`:
* Instrument `handle_event`:
* Log arrival of event: `event_type`, payload keys, and initial `needs_replanning` flag state.


* Log evaluation branches: Record boolean states of `state.review_due()`, `state.active_plan.is_exhausted()`, and prerequisite checks.


* Log target dispatch: `action_chosen`, dispatched worker name (`PlanningWorker` vs `TeachingWorker` vs `GraderComponent`), and routing latency in microseconds.






2. `src/goalcoach/application/progress_service.py`:
* Instrument `apply_grading_result`:
* Capture state diff before and after mutation:
```json
{
  "event": "progress_state_mutated",
  "concept_id": "hsk1_c01",
  "prior_mastery": 0.40,
  "new_mastery": 0.65,
  "stability_s": 3.42,
  "retention_r": 0.94,
  "next_review_days": 3.4,
  "needs_replanning_toggled": false
}

```


* Log `WARNING` if consecutive errors trigger `state.needs_replanning = True`.









### Phase 5: PydanticAI Reasoning Layer & LLM Gateway Failover

* **Goal:** Measure token economics, agent reasoning latency, schema repair loops, and hosted-to-local failovers.


* **Deliverables:**
1. `src/goalcoach/infrastructure/llm/pydantic_ai_models.py` (or gateway client):
* Log start of inference: `provider`, `model`, `prompt_length`, `timeout_seconds`.


* Log completion: `duration_ms`, `tokens.prompt`, `tokens.completion`, `retry_attempts`.


* Log failure & failover: If OpenRouter throws `httpx.TimeoutException` or HTTP 429, log `WARN` (`llm_primary_failed`) with the error stack, and log `INFO` (`llm_fallback_engaged`) when switching to local Ollama (`gemma-4`).




2. `src/goalcoach/agents/grader_component.py`:
* Fast-path logging: When deterministic evaluation succeeds (MCQ option or exact match), log `INFO` (`grader_fast_path_resolved`) with duration ($<1\text{ ms}$).


* LLM rubric logging: When fast-path misses, log `INFO` (`grader_llm_evaluated`) with `scores` (`syntax`, `semantics`, `pragmatics`), pass/fail gates, confidence, and `detected_errors`.




3. `src/goalcoach/infrastructure/persistence/content_service.py`:
* Instrument agent tools (`get_concept`, `get_prerequisites`, `synthesize_matching_exercise`): Log query parameters, result count, and execution time.







### Phase 6: CLI Harness & Local Developer Experience

* **Goal:** Ensure CLI sessions in `terminal_harness.py` surface telemetry cleanly without cluttering the interactive terminal interface.


* **Deliverables:**
1. `src/goalcoach/agents/terminal_harness.py`:
* Configure logging to write detailed structured JSON to a rotating log file (`~/.goalcoach/goalcoach.log` or `./logs/goalcoach.log`) while keeping stdout clean for interactive study panels.


* Add `--verbose` / `--debug` CLI flag to toggle live colored development logs directly in the terminal console.





### Phase 7: Verification Suite & Quality Assurance

* **Goal:** Enforce testing of log structure, context propagation, and performance invariants.


* **Deliverables:**
1. `tests/unit/test_observability.py`:
* *Test 1 (Context Isolation):* Verify that `bind_context` maintains distinct request IDs across concurrent `asyncio` tasks.
* *Test 2 (JSON Formatter Contract):* Ensure log records emit valid JSON with all required standard fields (`timestamp`, `level`, `context`, `message`).
* *Test 3 (Secret Scrubbing):* Verify that strings matching API key patterns are replaced with `***REDACTED***`.
* *Test 4 (FastAPI Middleware Integration):* Send request via `httpx.AsyncClient(app=app)`; assert headers contain `X-Request-ID` and logs record matching status code.


* *Test 5 (SQLAlchemy Listener):* Execute a query; verify cursor hooks measure duration without errors.





---

## 5. Architectural Decision Matrix (For the Coding Agent)

| Technical Decision | Recommended Approach | Alternative Considered | Trade-off Rationale |
| --- | --- | --- | --- |
| **Logging Library** | **Python Standard Library `logging**` with custom JSON formatter & context injection | `structlog` or `loguru` | `structlog` adds extra dependencies. GoalCoach already has `opentelemetry-api` and standard `logging` in `pyproject.toml`. Standard `logging` + `contextvars` is zero-dependency, highly performant, and fully compatible with Uvicorn/SQLAlchemy.

 |
| **Context Propagation** | **Python `contextvars**` | Passing context dictionaries through domain functions | Modifying domain functions (`route(state, ctx)`, `apply_grading(state, result, ctx)`) breaks domain boundaries and pollutes clean architecture. `contextvars` provides thread/task-local storage natively.

 |
| **Output Format** | **Dual Formatter Strategy** (NDJSON for prod/CI, Rich Color for CLI/dev) | Strict JSON everywhere | Reading JSON logs in an interactive CLI terminal harness ruins developer experience. Dynamic selection based on `GOALCOACH_ENVIRONMENT` yields optimal DX and machine observability.

 |
| **Database Profiling** | **SQLAlchemy Core Event Listeners** | Custom Repository Wrapper Functions | Wrapping repository methods only measures high-level method calls, missing query compilation, connection checkout, and SQLite lock wait times. Cursor events measure true engine execution.

 |

---

## 6. Ready-to-Execute Agent Directive / Task Prompt

```markdown
# TASK: Implement Enterprise Structured Logging & Observability Layer

## 1. Objective
Implement a production-grade, asynchronous structured logging and observability layer across GoalCoach. The system must measure API traffic, dual SQLite database operations, deterministic state machine routing, PydanticAI agent reasoning, model failovers, and spaced repetition progress math.

```

---

## 2. Invariants & Implementation Standards

1. Zero Blocking Overhead: Fast-path evaluations (<1ms) must not suffer I/O wait.
2. Context Propagation: Use `contextvars` to pass `request_id`, `trace_id`, and `learner_id` across async boundaries.
3. NDJSON in Production: Non-local environments emit single-line JSON. Local environments use readable console formatting.
4. Security: Scrub all API keys (`GOALCOACH_LLM_API_KEY`), tokens, and auth headers before output.
5. Standard Conventions: Align attribute names with OpenTelemetry specifications (`http.route`, `db.system`, `gen_ai.request.model`).

---

## 3. Detailed Step-by-Step Instructions

### Step 1: Core Logging Module (`src/goalcoach/infrastructure/logging/`)

1. Create `context.py`:
* Implement `ContextVar` instances: `ctx_trace_id`, `ctx_request_id`, `ctx_learner_id`.
* Provide `bind_context(**kwargs)`, `get_context() -> dict[str, Any]`, and `clear_context()`.


2. Create `formatters.py`:
* Implement `JSONFormatter(logging.Formatter)`: Format records into single-line JSON containing `timestamp` (ISO UTC), `level`, `logger`, `message`, `context` (from `context.py`), and any extra attributes passed via `extra={...}`.
* Implement `DevelopmentFormatter(logging.Formatter)`: Colorized, human-readable console string.


3. Create `filters.py`:
* Implement `SecretScrubbingFilter(logging.Filter)`: Redact API keys and bearer tokens with `***REDACTED***`.
* Implement `ContextFilter(logging.Filter)`: Attach active context values directly to the log record.


4. Create `config.py`:
* Implement `configure_logging(environment: str = "development", log_level: str = "INFO")`.
* Attach handlers with `SecretScrubbingFilter` and `ContextFilter`.
* Set log level for `goalcoach`, `apps.api`, `sqlalchemy.engine`, and `uvicorn.access`.



### Step 2: HTTP Middleware (`apps/api/middleware/observability.py`)

1. Create `ObservabilityMiddleware(BaseHTTPMiddleware)`:
* Extract or generate `X-Request-ID` and `trace_id`.
* Bind to `context.py`.
* Record start time with `time.perf_counter()`.
* Process request.
* Calculate latency in milliseconds.
* Emit `INFO` log with `http.method`, `http.route`, `http.status_code`, `duration_ms`.
* Add `X-Request-ID` and `X-Response-Time-Ms` to response headers.


2. In `apps/api/main.py`:
* Call `configure_logging(...)` inside lifespan startup.
* Register `ObservabilityMiddleware`.



### Step 3: SQLite Database Instrumentation (`src/goalcoach/infrastructure/persistence/database.py`)

1. Attach SQLAlchemy event hooks:
* `@event.listens_for(engine, "before_cursor_execute")`: Record execution start time.
* `@event.listens_for(engine, "after_cursor_execute")`: Compute execution time. If `duration_ms > 25.0`, emit `WARN` (`db_slow_query`); otherwise, emit `DEBUG` (`db_query_executed`).
* `@event.listens_for(engine, "handle_error")`: Emit `ERROR` (`db_query_failed`) with sanitized error details.



### Step 4: Decision & Progress Telemetry

1. In `src/goalcoach/application/orchestrator.py`:
* Log `INFO` on event dispatch: `event_type`, payload summary.
* Log `INFO` on route resolution: evaluated condition states (`review_due`, `needs_replanning`), chosen action, elapsed microseconds.


2. In `src/goalcoach/application/progress_service.py`:
* Log `INFO` on state mutation: `concept_id`, prior mastery vs updated mastery, retrievability, stability, next review date.
* Log `WARN` if repeated errors set `state.needs_replanning = True`.



### Step 5: Grader, Agent & Model Gateway Instrumentation

1. In `src/goalcoach/agents/grader_component.py`:
* Fast-path match: Log `INFO` (`grader_fast_path`) with normalized answer, pass/fail result, and execution time (<1ms).
* LLM rubric evaluation: Log `INFO` (`grader_llm_evaluated`) with multi-axis scores, confidence, detected error codes.


2. In `src/goalcoach/infrastructure/llm/pydantic_ai_models.py` (or gateway runner):
* Instrument inference: Log model, provider, prompt length, completion latency, token counts.
* Failover interceptor: On OpenRouter failure, log `WARN` (`llm_fallback_triggered`) with the root error and fallback model details.


3. In `src/goalcoach/infrastructure/persistence/content_service.py`:
* Log `DEBUG` on tool methods (`get_concept`, `get_prerequisites`, `synthesize_matching_exercise`): arguments, duration, item count.



### Step 6: Test Suite

Create `tests/unit/test_observability.py`:

1. Test context variable isolation across async tasks.
2. Test `JSONFormatter` produces valid JSON with expected keys.
3. Test `SecretScrubbingFilter` scrubs configured API tokens.
4. Test `ObservabilityMiddleware` attaches request IDs and returns timing headers.
5. Test database listener measures dummy query without error.

---

## 4. Verification Commands

```bash
# 1. Format and lint checks
uv run ruff check src/ apps/ tests/
uv run ruff format --check src/ apps/ tests/

# 2. Run unit tests including new observability suite
uv run pytest tests/unit/ -v

# 3. Run full integration verification
GOALCOACH_ENVIRONMENT="testing" \
GOALCOACH_LLM_API_KEY="ci-mock-token" \
uv run pytest tests/integration/ -v

```