# Changelog

All notable changes to the GoalCoach project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0-mvp] - 2026-09-17

### Added
- **Closed State-Driven Agentic Architecture**: Proved the foundational learning loop: `Goal -> Plan -> Teach -> Grade -> Update State -> Adapt -> Re-plan`.
- **Deterministic Orchestrator** (`src/goalcoach/application/orchestrator.py`): Pure Python event routing for `GOAL_CREATED`, `SESSION_STARTED`, `ANSWER_SUBMITTED`, and `HELP_REQUESTED` without LLM orchestration overhead.
- **PydanticAI Planning Worker** (`src/goalcoach/agents/planning_agent.py`): Adaptive curriculum planner generating validated `PlanUpdate` schemas based on daily time budgets, retention decay, and historical weaknesses.
- **PydanticAI Teaching Worker** (`src/goalcoach/agents/teaching_agent.py`): Adaptive pedagogy worker selecting instructional modalities (`EXPLANATION`, `HINT`, `CONTRAST_EXAMPLE`, `EXERCISE`, `DIALOGUE`, `RETRY`).
- **Grader Component** (`src/goalcoach/agents/grader_component.py`): Isolated evaluator featuring deterministic exact-match fast-path and LLM rubric grading across syntax, semantics, and pragmatics.
- **Mathematical Progress Engine** (`src/goalcoach/application/progress_service.py`): Deterministic 40/40/20 reducer, exponential retention decay, and spaced repetition intervals.
- **Dual SQLite Persistence Layer**:
  - Database #1 (`data/database1/goalcoach_hsk1_learning.db`): Grounded static HSK 1 curriculum concepts, cards, and prerequisite relationships.
  - Database #2 (`goalcoach.db`): Dynamic learner state in WAL mode (`LearnerRepository`).
- **Content Service** (`src/goalcoach/infrastructure/persistence/content_service.py`): Sub-millisecond SQL lookup engine replacing vector retrieval overhead for core HSK 1 content.
- **Dual Model Gateway**:
  - Primary hosted model: `inclusionai/ling-3.0-flash-fin` (via OpenRouter or OpenAI-compatible endpoint).
  - Fallback local model: `hf.co/unsloth/gemma-4-E4B-it-GGUF:Q4_K_M` or `gemma-4-E2B-it-GGUF:Q4_K_M` via Ollama.
  - Resilient automatic failover when hosted endpoints fail. More models will be tested and added in future iterations.
- **Interactive Terminal Harness** (`src/goalcoach/agents/terminal_harness.py`): CLI interface enabling end-to-end interactive learning and grading sessions in the console.
- **Unified REST API** (`apps/api/`):
  - `POST /api/v1/events`: Core closed-loop event gateway.
  - `POST /api/v1/tutoring/chat`: Conversational tutoring endpoint.
  - `GET /health`: System health and connectivity checks.
- **Modern Web Application** (`apps/web/`): React 18 + Vite SPA with interactive pinyin charts, visual roadmap, and drawer coaching components.
- **Automated CI Workflow** (`.github/workflows/ci.yml`): Continuous integration verifying `uv lock`, `ruff check`, `ruff format`, and unit/integration test suites on pull requests.
- **Comprehensive Test Suites**:
  - Unit tests covering progress math, reducers, and API contracts (67 tests).
  - Integration tests verifying Acceptance Criteria AC1 through AC11 (`tests/integration/test_closed_loop.py`).
  - Edge-case remediation tests (`tests/integration/test_remediation_loop.py`).

### Fixed
- **Infinite Remediation Stagnation**: Implemented dynamic exercise rotation to guarantee that failed remedial exercises do not loop on repeated item IDs.
- **Prerequisite DAG Stepping Gap**: Fixed blocker where remediating an upstream prerequisite failed to unlock unready downstream concepts.
- **Pydantic Validation Error in Error Decrement**: Fixed `ValidationError` caused by attempting to decrement `occurrences` to `0` in `ErrorRecord` (which enforces `ge=1`) by explicitly purging resolved errors.
- **Error Code Length Limitation**: Increased `ErrorRecord.code` field limit from 64 to 255 characters to support rich error categorization tags.
- **CI Database Missing Table Error**: Configured automated curriculum database bootstrapping in CI runner from the SQL package.
- **Linter & Formatter Alignment**: Resolved Ruff lint violations (`B008`, `F821`, `SIM102`, `C414`, `BLE001`) and formatted entire codebase to zero diffs.

---

## [0.1.0-beta] - 2026-09-08

### Added
- Embedded ChromaDB vector retrieval pipeline for semantic concept card matching (`src/goalcoach/infrastructure/retrieval/chroma_service.py`).
- PydanticAI initial teaching and rubric grading agents.
- OpenRouter failover to Ollama Gemma models.
- Streamlit prototype interface (`apps/web/app.py`).

---

## [0.1.0-alpha] - 2026-09-01

### Added
- Initial project scaffolding and dependency management via Astral `uv`.
- Static HSK 1 curriculum SQLite database and relational schema (`curriculum_concepts`, `curriculum_cards`, `prerequisites`).
- Core Pydantic domain models for `LearnerState`, `ConceptMastery`, `DailyPlan`, and `GradingResult`.
