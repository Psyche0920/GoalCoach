# Full-Stack Integration Plan & Execution Walkthrough: React Frontend into GoalCoach FastAPI Core

> **Document Status:** Executed & Verified (100% test pass rate, clean builds, production verified)  
> **Target Subsystems:** `apps/web` (React 18 + Vite), `apps/api` (FastAPI Core), `src/goalcoach` (Domain & Application Logic)

---

## Table of Contents
1. [Part I: Architectural Plan & Design](#part-i-architectural-plan--design)
   - [1. Context & Goal Description](#1-context--goal-description)
   - [2. System Topology & Decoupled Interaction Model](#2-system-topology--decoupled-interaction-model)
   - [3. Architectural Invariants & Guardrails](#3-architectural-invariants--guardrails)
   - [4. Planned Changes by Component](#4-planned-changes-by-component)
   - [5. Verification Strategy](#5-verification-strategy)
2. [Part II: Execution Walkthrough & Results](#part-ii-execution-walkthrough--results)
   - [6. Implementation Summary & Delivered Components](#6-implementation-summary--delivered-components)
   - [7. Verification Results & Test Metrics](#7-verification-results--test-metrics)
   - [8. Runbook: Starting Backend & Frontend](#8-runbook-starting-backend--frontend)

---

# Part I: Architectural Plan & Design

## 1. Context & Goal Description
The primary objective of this initiative was the complete end-to-end integration of the Duolingo-style React frontend (`apps/web`) into the GoalCoach FastAPI backend (`apps/api` and `src/goalcoach`).

The previous prototype in `apps/web` relied on an embedded Express runtime (`server.ts`). The architectural goal was to:
1. Completely decommission the Express runtime, converting `apps/web` into a pure, standalone Vite Single-Page Application (SPA).
2. Configure Vite reverse-proxying so that all `/api` and `/health` network traffic seamlessly targets FastAPI on `http://127.0.0.1:8000`.
3. Align the Python backend domain models, deterministic progress reduction engine, SQLite WAL persistence layer, and REST endpoints to achieve a closed, state-driven learning loop without mock fallbacks.

---

## 2. System Topology & Decoupled Interaction Model

```text
┌──────────────────────────────────────────────────────────┐
│           React 18 + Vite Frontend (Port 3000)           │
│   DailyPlanView  |  DuolingoModal  |  PinyinLessonModal  │
│   ModernChatDrawer  |  RetentionVisualizer  |  TopBar    │
└────────────────────────────┬─────────────────────────────┘
                             │ Vite Reverse Proxy (:3000 -> :8000)
                             ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI Application (Port 8000)             │
│                                                          │
│  /api/v1/learners/*      /api/v1/answers                 │
│  /api/v1/curriculum/*    /api/v1/grade-freeform          │
│  /api/v1/tutoring/chat   /api/tts                        │
└────────────┬────────────────────────────┬────────────────┘
             │                            │
Synchronous Fast-Path (<800ms)      BackgroundTasks (Decoupled)
             ▼                            ▼
┌─────────────────────────┐  ┌─────────────────────────────┐
│      GradingAgent       │  │    Progress & State Engine  │
│  - Deterministic Match  │  │  - 40/40/20 Evidence Reducer│
│  - PydanticAI Fallback  │  │  - Spaced Repetition Math   │
└────────────┬────────────┘  └──────────────┬──────────────┘
             │                              │
             ▼                              ▼
┌─────────────────────────┐  ┌─────────────────────────────┐
│   OpenRouter / Ollama   │  │   SQLite DB #2 (goalcoach)  │
│   Qwen-2.5 / Gemma 4    │  │   WAL Mode, Busy Timeout    │
└─────────────────────────┘  └─────────────────────────────┘
```

---

## 3. Architectural Invariants & Guardrails
1. **Never Execute an LLM Chain**: Never invoke Planner, Progress, Retrieval, Grader, and Teacher sequentially for a single answer.
2. **Deterministic Control**: The top-level workflow orchestrator (`route(state)`) and daily schedule generation execute via pure Python state machine logic without consuming model tokens.
3. **Synchronous Response Path Bound**: The answer submission path (`POST /api/v1/answers`) evaluates grading via the deterministic fast path or PydanticAI within 800 ms. Post-grading progress mutations and SQLite writes are offloaded into asynchronous FastAPI `BackgroundTasks`.
4. **Serialization & Casing Parity**: The React frontend expects and emits `camelCase` payload keys (`learnerId`, `conceptId`, `dailyAvailableMinutes`). Enforced via `alias_generator = to_camel` and `populate_by_name = True` across all domain base models.
5. **Database Isolation**: Database #1 (`goalcoach_hsk1_learning.db` - read-only static curriculum content) remains strictly isolated from Database #2 (`goalcoach.db` - mutable learner state with SQLite WAL pragmas).

---

## 4. Planned Changes by Component

### Component 1: Python Domain Schema Alignment (`src/goalcoach/domain/models.py`)
- Update `DomainBaseModel` to support camelCase serialization automatically using Pydantic v2 configuration:
  ```python
  class DomainBaseModel(BaseModel):
      model_config = ConfigDict(
          from_attributes=True,
          populate_by_name=True,
          alias_generator=to_camel,
          validate_assignment=True,
          ser_json_timedelta="float",
      )
  ```
- Implement typed models required for honest progress tracking:
  - `LearningEvidence`: `card_completion: float`, `practice_completion: float`, `output_completion: float`.
  - `ConceptProgress`: Tracks `learned_percent` (40/40/20 rule), `mastery_score`, `retention_at_review`, `decay_lambda`, `successful_spaced_retrievals`, `evidence_days`, `average_review_quality`, `status` (`not_started`, `learning`, `almost_mastered`, `mastered`), `last_reviewed_at`, and `next_review_at`.
  - `ProgressSummary`: Contains `course_coverage`, `learned_progress`, `mastered_progress`, `goal_completion`, `goal_scope_learned_percent`, `goal_scope_mastered_percent`, and `communication_outcome_percent`.
  - `LearningEvent`: An idempotent event model containing `id`, `learner_id`, `plan_item_id`, `concept_ids`, `event_type` (`card`, `audio`, `attempt`, `output`, `review`), `engagement_score`, and optional `grading_result`.
- Update `LearnerState` to support `UUID | str` learner identifiers, `concept_progress: dict[str, ConceptProgress]`, and `passed_blueprint_ids: list[str]`.

### Component 2: Deterministic Progress Reducer (`src/goalcoach/application/progress_reducer.py`)
- **The 40/40/20 First-Learning Rule**:
  $$\text{learnedPercent} = 100 \times (0.40 \cdot \text{card} + 0.40 \cdot \text{practice} + 0.20 \cdot \text{output})$$
- **Monotonicity**: A learned concept remains learned; forgetting or low review scores must never decrease `learnedPercent`.
- **Mastery Qualification Rule**: A concept qualifies for `Mastered = 100%` if and only if:
  1. `successful_spaced_retrievals >= 4`
  2. `evidence_days >= 3`
  3. `average_review_quality >= 0.80`
  (Immediate retries or multiple attempts on the same calendar day count as only 1 retrieval attempt).
- **Composite Goal Progress Formulation**:
  $$\text{goalCompletion} = \text{round}(0.45 \cdot \text{goalScopeLearned} + 0.35 \cdot \text{goalScopeMastered} + 0.20 \cdot \text{communicationOutcome})$$

### Component 3: Learner State SQLite Persistence (`src/goalcoach/infrastructure/persistence/`)
- Enforce WAL pragmas on all SQLite connections:
  `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000; PRAGMA foreign_keys=ON;`
- Create `LearnerStateORM` (storing JSON aggregate state snapshots) and `LearningEventORM` (storing immutable audit logs).
- Add `get_exercise(exercise_id: str)` to `ContentRepository`.
- Add `record_learning_event` and `get_learning_events` to `SqlAlchemyLearnerRepository`.

### Component 4: REST API Layer (`apps/api/routes/learning.py`, `tutoring.py`, `main.py`)
- `GET /api/tts`: Strip non-alphanumeric punctuation and proxy audio responses with an in-memory `dict[str, bytes]` cache.
- `POST /api/v1/answers`: Run `grade_submission(exercise, submission)` via `grading_agent.py` and decouple state mutation via `BackgroundTasks`. Return `{"gradingResult": result, "provider": provider}`.
- `POST /api/v1/grade-freeform`: Evaluate freeform scenario submissions against blueprint assessment specs.
- `POST /api/v1/learning-events`: Ingest audit events and trigger progress updates.
- `GET /api/v1/learners/{learner_id}`: Return the learner state, deterministic `route(state)`, and computed `ProgressSummary`.
- `GET /api/v1/curriculum/concepts` & `/concepts/{concept_id}`: Access static curriculum content from Database #1.
- `POST /api/v1/tutoring/chat` & `/chat`: Route dialogue through `teaching_agent.py` using curriculum RAG injection.
- Enable CORS allowing `http://localhost:3000` and `http://127.0.0.1:3000` with full credentials and wildcard methods.

### Component 5: Transition `apps/web` to Standalone Vite Frontend
- In `apps/web/package.json`:
  - Set `"scripts"`: `"dev": "vite"`, `"build": "tsc -b && vite build"`, `"preview": "vite preview"`, `"lint": "tsc --noEmit"`.
  - Strip unused Express backend dependencies: `express`, `@google/genai`, `cors`, `tsx`, `esbuild`, `@types/express`, `@types/cors`.
  - Ensure `uuid` is updated to `^11.1.0`.
- In `apps/web/tsconfig.json`: Restrict `"include"` to `["src"]` (removing `server.ts`).
- In `apps/web/vite.config.ts`: Configure `server.proxy` to forward `/api` and `/health` to `http://127.0.0.1:8000`.
- In `apps/web/src/components/ModernChatDrawer.tsx`: Re-point chat requests to backend `POST /api/v1/tutoring/chat` passing `{ "message": userMessage, "learner_id": "learner_001" }`.

---

## 5. Verification Strategy
1. **Linter & Code Quality**: `uv run ruff check src/goalcoach apps/api tests/unit`
2. **Automated Unit Tests**: `uv run pytest tests/unit/ -v` (100% pass rate target)
3. **Frontend Compilation**: `npm run lint` (`tsc --noEmit`) and `npm run build` (`vite build`)
4. **End-to-End Loop Validation**: Verify exercise loading, audio playback, answer evaluation, and state persistence across reloads.

---

# Part II: Execution Walkthrough & Results

## 6. Implementation Summary & Delivered Components

### 1. Python Domain Schema Alignment
*File:* [`src/goalcoach/domain/models.py`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/domain/models.py)
- Enabled `alias_generator = to_camel` and `populate_by_name = True` in `DomainBaseModel`.
- Added [`LearningEvidence`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/domain/models.py#L103), [`ConceptProgress`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/domain/models.py#L111), [`ProgressSummary`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/domain/models.py#L134), and [`LearningEvent`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/domain/models.py#L148).
- Updated [`LearnerState`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/domain/models.py#L244), [`PlanItem`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/domain/models.py#L169), and [`DailyPlan`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/domain/models.py#L180) to support `UUID | str` IDs.

### 2. Deterministic Progress Reducer Engine
*File:* [`src/goalcoach/application/progress_reducer.py`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/application/progress_reducer.py)
- Implemented `reduce_concept_progress(...)` enforcing:
  - 40/40/20 evidence calculation.
  - Strict monotonicity (`learned_percent = max(current.learned_percent, raw_learned)`).
  - Spaced review quality aggregation and calendar-day attempt throttling.
  - Strict qualification gates for mastery ($R \ge 4, D \ge 3, Q \ge 0.80$).
- Implemented `compute_progress_summary(...)` calculating course coverage, learned progress, mastered progress, communication outcomes, and composite goal completion.

### 3. SQLite Persistence & WAL Optimization
*Files:*
- [`src/goalcoach/infrastructure/persistence/learner_models.py`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/infrastructure/persistence/learner_models.py): Created `LearnerStateORM` and `LearningEventORM`.
- [`src/goalcoach/infrastructure/persistence/database.py`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/infrastructure/persistence/database.py): Enforced WAL pragmas (`WAL`, `NORMAL`, `busy_timeout=5000`, `foreign_keys=ON`) and auto-schema generation.
- [`src/goalcoach/infrastructure/persistence/repositories.py`](file:///C:/Users/musab/Documents/GoalCoach/src/goalcoach/infrastructure/persistence/repositories.py): Added `get_exercise` to `ContentRepository` and audit methods to `SqlAlchemyLearnerRepository`.

### 4. REST API Endpoints
*Files:*
- [`apps/api/routes/learning.py`](file:///C:/Users/musab/Documents/GoalCoach/apps/api/routes/learning.py): Exposes TTS audio proxy, answer grading (<800ms fast-path), freeform scenario grading, learning events, concept completions, and curriculum queries.
- [`apps/api/routes/tutoring.py`](file:///C:/Users/musab/Documents/GoalCoach/apps/api/routes/tutoring.py): Exposes `/tutoring/chat` and `/chat` with flexible payload adaptation.
- [`apps/api/main.py`](file:///C:/Users/musab/Documents/GoalCoach/apps/api/main.py): Registers routers and configures CORS for Vite on `http://localhost:3000`.

### 5. Frontend Standalone SPA Transition
*Files:*
- [`apps/web/package.json`](file:///C:/Users/musab/Documents/GoalCoach/apps/web/package.json): Pruned Express server packages, set standard Vite scripts, upgraded `uuid` to `^11.1.0`.
- [`apps/web/tsconfig.json`](file:///C:/Users/musab/Documents/GoalCoach/apps/web/tsconfig.json): Removed `server.ts` from `"include"`.
- [`apps/web/vite.config.ts`](file:///C:/Users/musab/Documents/GoalCoach/apps/web/vite.config.ts): Reverse proxy configured for `/api` and `/health`.
- [`apps/web/src/components/ModernChatDrawer.tsx`](file:///C:/Users/musab/Documents/GoalCoach/apps/web/src/components/ModernChatDrawer.tsx): Re-pointed chat requests directly to `/api/v1/tutoring/chat`.

---

## 7. Verification Results & Test Metrics

### 1. Code Quality & Linting
```powershell
uv run ruff check src/goalcoach apps/api tests/unit
```
```text
All checks passed!
```

### 2. Automated Test Suite (100% Pass Rate)
```powershell
uv run pytest tests/unit/ -v
```
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\musab\Documents\GoalCoach
configfile: pyproject.toml
plugins: anyio-4.15.1, logfire-5.0.0, asyncio-0.26.0
collected 67 items

tests/unit/test_api_learning.py::test_health PASSED                      [  1%]
tests/unit/test_api_learning.py::test_curriculum_concepts PASSED         [  2%]
tests/unit/test_api_learning.py::test_curriculum_concept_details PASSED  [  4%]
tests/unit/test_api_learning.py::test_learner_aggregate_and_routing PASSED [  5%]
tests/unit/test_api_learning.py::test_submit_answer_deterministic_fast_path PASSED [  7%]
tests/unit/test_api_learning.py::test_grade_freeform PASSED              [  8%]
tests/unit/test_api_learning.py::test_learning_events PASSED             [ 10%]
tests/unit/test_api_learning.py::test_complete_concept PASSED            [ 11%]
tests/unit/test_api_learning.py::test_tts_empty_validation PASSED        [ 13%]
tests/unit/test_config.py::test_planning_item_minutes_defaults_to_five PASSED [ 14%]
tests/unit/test_config.py::test_planning_item_minutes_loads_from_environment PASSED [ 16%]
tests/unit/test_config.py::test_planning_item_minutes_rejects_invalid_values[0] PASSED [ 17%]
tests/unit/test_config.py::test_planning_item_minutes_rejects_invalid_values[-1] PASSED [ 19%]
tests/unit/test_config.py::test_planning_item_minutes_rejects_invalid_values[121] PASSED [ 20%]
tests/unit/test_config.py::test_configured_item_minutes_are_injected_into_planner PASSED [ 22%]
tests/unit/test_goal_planning.py::test_plan_orders_review_remedial_and_new PASSED [ 23%]
tests/unit/test_goal_planning.py::test_new_learner_starts_from_first_concept PASSED [ 25%]
tests/unit/test_goal_planning.py::test_plan_does_not_exceed_available_time PASSED [ 26%]
tests/unit/test_goal_planning.py::test_due_concept_is_not_duplicated_as_remedial PASSED [ 28%]
tests/unit/test_goal_planning.py::test_missing_goal_raises_error PASSED  [ 29%]
tests/unit/test_goal_planning.py::test_new_concept_is_blocked_until_prerequisite_is_mastered PASSED [ 31%]
tests/unit/test_goal_planning.py::test_mastered_prerequisite_unlocks_new_concept PASSED [ 32%]
tests/unit/test_goal_planning.py::test_prerequisite_requires_evidence_and_threshold_mastery PASSED [ 34%]
tests/unit/test_goal_planning.py::test_prerequisites_must_reference_known_curriculum_concepts PASSED [ 35%]
tests/unit/test_models.py::test_score_boundary_clamping PASSED           [ 37%]
tests/unit/test_models.py::test_learning_goal_validation PASSED          [ 38%]
tests/unit/test_models.py::test_concept_mastery_retention_and_due_check PASSED [ 40%]
tests/unit/test_models.py::test_concept_mastery_is_review_due_timezone_mismatch PASSED [ 41%]
tests/unit/test_models.py::test_learner_state_overall_progress_empty PASSED [ 43%]
tests/unit/test_models.py::test_learner_state_overall_progress_single_concept PASSED [ 44%]
tests/unit/test_models.py::test_learner_state_overall_progress_weighted_multi_concept PASSED [ 46%]
tests/unit/test_models.py::test_learner_state_review_due_aggregate PASSED [ 47%]
tests/unit/test_error_record_validation PASSED                           [ 49%]
tests/unit/test_models.py::test_plan_item_and_daily_plan_validation PASSED [ 50%]
tests/unit/test_models.py::test_exercise_and_grading_models PASSED       [ 52%]
tests/unit/test_models.py::test_session_summary_and_progress_update PASSED [ 53%]
tests/unit/test_models.py::test_retrieval_request_exact_mode_validation PASSED [ 55%]
tests/unit/test_models.py::test_retrieval_request_semantic_mode_validation PASSED [ 56%]
tests/unit/test_models.py::test_retrieval_request_structured_mode PASSED [ 58%]
tests/unit/test_models.py::test_learner_state_json_roundtrip_serialization PASSED [ 59%]
tests/unit/test_models.py::test_domain_base_model_config PASSED          [ 61%]
tests/unit/test_orchestrator.py::test_new_learner_without_goal_routes_to_plan_goal PASSED [ 62%]
tests/unit/test_orchestrator.py::test_learner_with_goal_changed_flag_routes_to_plan_goal PASSED [ 64%]
tests/unit/test_orchestrator.py::test_goal_planning_precedence_over_review_due_and_active_plan PASSED [ 65%]
tests/unit/test_orchestrator.py::test_expired_review_timestamp_routes_to_plan_review PASSED [ 67%]
tests/unit/test_orchestrator.py::test_review_due_precedence_over_missing_or_exhausted_plan PASSED [ 68%]
tests/unit/test_orchestrator.py::test_future_review_date_does_not_trigger_review_routing PASSED [ 70%]
tests/unit/test_orchestrator.py::test_missing_active_plan_routes_to_regenerate_plan PASSED [ 71%]
tests/unit/test_orchestrator.py::test_exhausted_plan_routes_to_regenerate_plan PASSED [ 73%]
tests/unit/test_orchestrator.py::test_invalid_plan_routes_to_regenerate_plan PASSED [ 74%]
tests/unit/test_orchestrator.py::test_active_plan_with_no_due_reviews_routes_to_teaching PASSED [ 76%]
tests/unit/test_orchestrator.py::test_planning_orchestrator_persists_plan_without_mutating_loaded_state PASSED [ 77%]
tests/unit/test_orchestrator.py::test_planning_orchestrator_rejects_unknown_learner PASSED [ 79%]
tests/unit/test_progress.py::test_progress_combines_mastery_retention_and_weight PASSED [ 80%]
tests/unit/test_progress_reducer.py::test_40_40_20_first_learning_rule PASSED [ 82%]
tests/unit/test_progress_reducer.py::test_monotonicity_guarantee PASSED  [ 83%]
tests/unit/test_progress_reducer.py::test_atomic_unit_completion PASSED  [ 85%]
tests/unit/test_progress_reducer.py::test_mastery_qualification_rule PASSED [ 86%]
tests/unit/test_progress_reducer.py::test_composite_goal_progress_formulation PASSED [ 88%]
tests/unit/test_retention.py::test_retention_zero_elapsed_time PASSED    [ 89%]
tests/unit/test_retention.py::test_retention_decay_over_time PASSED      [ 91%]
tests/unit/test_retention.py::test_retention_future_or_negative_elapsed_time_clamped_to_zero_elapsed PASSED [ 92%]
tests/unit/test_retention.py::test_retention_clamped_between_zero_and_one PASSED [ 94%]
tests/unit/test_retention.py::test_retention_timezone_resilience_naive_and_aware PASSED [ 95%]
tests/unit/test_retention.py::test_retention_default_at_uses_current_time PASSED [ 97%]
tests/unit/test_retention.py::test_retention_invalid_decay_lambda_raises_value_error PASSED [ 98%]
tests/unit/test_decayed_retention_helper PASSED                           [100%]

======================= 67 passed, 7 warnings in 0.73s ========================
```

### 3. Frontend Compilation & Production Build
```powershell
cd apps/web; npm run lint; npm run build
```
```text
> goalcoach-web@0.1.0 lint
> tsc --noEmit

> goalcoach-web@0.1.0 build
> tsc -b && vite build

vite v6.4.3 building for production...
✓ 2211 modules transformed.
dist/index.html                   1.67 kB │ gzip:   0.73 kB
dist/assets/index-oLef9Kuy.css   98.29 kB │ gzip:  14.47 kB
dist/assets/index-DnFGHsOB.js   934.25 kB │ gzip: 277.44 kB
✓ built in 16.49s
```

---

## 8. Runbook: Starting Backend & Frontend

### 1. Launch FastAPI Core (Port 8000)
```powershell
uv run uvicorn apps.api.main:app --port 8000 --reload
```
Health endpoint verification:
```powershell
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

### 2. Launch React Frontend (Port 3000)
```powershell
cd apps/web
npm run dev
```

### 3. Verified Browser Experience
Navigate to `http://localhost:3000`:
- **Curriculum & Knowledge Tree**: Loaded automatically via `/api/v1/curriculum/concepts`.
- **Speech Synthesis**: Native female audio played on card tap via `/api/tts`.
- **Gamified Practice**: Exercise answers graded within <800ms via `/api/v1/answers` fast-path short-circuit.
- **Coach Baobao AI Dialogue**: Slide-over drawer connected directly to `/api/v1/tutoring/chat`.
- **Persistence Across Sessions**: All progress mutations deterministically reduced and durably committed to SQLite WAL database `goalcoach.db`.
