# Changelog

All notable changes to the GoalCoach project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.1] - 2026-09-21

### Added
- **Pedagogical Pre-Selection & Context Synchronization**:
  - Implemented `_select_candidate_exercise()` in `src/goalcoach/agents/teaching_agent.py` to pre-select candidate practice activities before LLM invocation, injecting the target upcoming exercise directly into the prompt so explanations are grounded, relevant, and bridge directly into practice.
- **Rich MCQ Options & 1-Click Answering**:
  - Attached `options` and `exercise_type` to `TeachingAction.exercise_payload` and `Exercise` domain model in `src/goalcoach/domain/models.py`.
  - Added fast-path index (`1`, `2`, `3`, `4`) and letter (`A`, `B`, `C`, `D`) option resolution in `src/goalcoach/agents/grader_component.py` and `src/goalcoach/application/orchestrator.py` (<5ms execution).
  - Enhanced terminal harness (`src/goalcoach/agents/terminal_harness.py`) to render formatted choices `(1)`, `(2)`, `(3)`, `(4)` for multiple-choice questions.
  - Added comprehensive integration test `test_mcq_options_in_payload_and_1_click_grading` in `tests/integration/test_remediation_loop.py`.

### Changed
- **Empathetic "Coach Baobao" Teaching Persona**: Upgraded system prompt in `src/goalcoach/agents/teaching_agent.py` to eliminate "naked exercises" on repeated learner errors (`failed_attempts >= 2`), ensuring patient scaffolding, emotional validation, and structural grammar breakdowns prior to retries.
- **Pedagogical Preservation of Open-Input Modalities**: Maintained authentic active-recall input for `fill_blank` and `translate_to_zh` exercises (supporting Hanzi and Pinyin responses) without artificial or synthetic distractors.
- **Sequential Curriculum Prerequisites Alignment**:
  - Realigned all `concept_prerequisites` in `data/database1/GoalCoach_HSK1_Learning_DB_Package/data/goalcoach_hsk1_learning_db_sqlite.sql` so that every concept strictly depends on its immediate predecessor in chronological curriculum sequence (from `hsk1_c02` -> `hsk1_c01` through `hsk6_c22` -> `hsk6_c21`), forming a clean linear progression across all 121 concepts (120 total edges).

### Fixed
- **Content Repository Prerequisite Assertions**: Updated `test_loads_all_prerequisite_relationships` in `tests/integration/test_content_repository.py` to assert the 120 total sequential prerequisite relationships, 19 HSK 1 rules, and `hsk1_c20` -> `hsk1_c19`.


## [0.1.0] - 2026-09-20

### Added
- **AI Agent Workspace Configuration & Customizations (`.agents/`)**:
  - **Code Review Subagent (`.agents/agents/code-reviewer/agent.md`)**: Configured an autonomous `code-reviewer` agent specification emphasizing Karpathy-inspired simplicity principles, OOP/SOLID Python architecture, surgical non-breaking modifications, and strict security rules (e.g., zero `.env` exposure).

### Removed
- **Vector Database (ChromaDB) Decommissioning**: Fully removed ChromaDB and all associated vector retrieval components in accordance with PRD Principle 6 ("Zero Heavy Vector DB Overload"):
  - Removed `src/goalcoach/infrastructure/retrieval/` directory (`chroma_service.py`, `chunk_factory.py`, and `__init__.py`).
  - Removed `src/goalcoach/agents/retrieval.py` (`RetrievalAgent` and `RemedialMaterial`).
  - Removed `scripts/vector_store.py` (offline ChromaDB extraction and indexing script).
  - Removed `tests/integration/test_vector_pipeline.py` (vector pipeline test suite).
  - Removed `docs/vector-database.md` engineering specification.
  - Removed local `data/database2/chroma_db` directory and cleaned `.gitignore`.
- **Heavy ML Dependencies**: Removed `chromadb>=0.6.3`, `sentence-transformers>=3.0.0`, and `posthog<3` from `pyproject.toml` (`[project.optional-dependencies.retrieval]`).
- **Dependency Pruning**: Pruned 38 transitive packages via `uv lock` (including PyTorch/torch, transformers, sentence-transformers, onnxruntime, flatbuffers, and CUDA libraries), reducing resolved dependencies from 244 to 187 packages and drastically reducing CI install overhead.
- **Retriever Protocol**: Removed unused `Retriever` protocol from `src/goalcoach/agents/interfaces.py` and `src/goalcoach/agents/__init__.py`.
- **Legacy Agent Specification**: Removed older `agent.md` from the root workspace in favor of the structured subagent architecture under `.agents/agents/code-reviewer/agent.md`.

### Changed
- **Deterministic Curriculum Retrieval**: Refactored `search_hsk_curriculum` in `src/goalcoach/agents/tools/retrieval_tools.py` to query the SQLite `ContentRepository` deterministically without ChromaDB fallback.
- **FastAPI Tutoring Chat Endpoint**: Decoupled `apps/api/routes/tutoring.py` and `apps/api/dependencies.py` from ChromaDB; removed `get_chroma_service` dependency injection and `ChromaService` startup instantiation in `apps/api/main.py`.
- **Configuration Simplification**: Removed `vector_store_path`, `chroma_persist_directory`, `_sync_vector_paths` validator, and `enable_vector_retrieval` flag from `src/goalcoach/infrastructure/config.py`.
- **Settings Resilience**: Configured `extra="ignore"` on `SettingsConfigDict` in `src/goalcoach/infrastructure/config.py` to prevent fatal startup validation crashes from deprecated environment variables.
- **PRD Documentation**: Updated Principle 6 in `docs/GOALCOACH_MVP_PRD.md` to record that the vector database has been permanently decommissioned in favor of deterministic `ContentService` querying SQLite Database #1.

### Fixed
- **Curriculum & Learning Content Licensing Rectification**: Corrected the license for the imported HSK curriculum and vocabulary learning materials in `data/`:
  - Identified dual-licensing structure in the upstream [wuxialearn](https://github.com/wuxialearn) project: while application client code is under MIT, language frequency dictionary and learning datasets are governed by **CC BY-NC-SA 4.0** ([WuxiaLearn Frequency Dictionary LICENSE](https://github.com/wuxialearn/Chinese-English-Frequency-Dictionary/blob/master/LICENSE)).
  - Replaced the erroneous root MIT copy in `data/LICENSE` with the complete **CC BY-NC-SA 4.0** license text and proper attribution to `wuxialearn`.
  - Updated `data/database1/GoalCoach_HSK1_Learning_DB_Package/data/goalcoach_hsk1_learning_db_sqlite.sql` header comments to reference CC BY-NC-SA 4.0 and `data/LICENSE`.
  - Updated `docs/dev/goalcoach_hsk1_learning.db.md` with explicit attribution and licensing boundaries separating application software (MIT) from educational content (CC BY-NC-SA 4.0).
- **CI Integration Test Failures from Expanded Curriculum**:
  - **Prerequisite Count Assertion**: Updated `test_loads_all_prerequisite_relationships` in `tests/integration/test_content_repository.py` to assert the 120 total sequential prerequisite relationships in the expanded dataset.
  - **Exercise Exhaustion Graceful Fallback**: Updated `test_edge_case_exercise_exhaustion_graceful_fallback` in `tests/integration/test_remediation_loop.py` to dynamically query all exercises for `hsk1_c01` before simulating exercise exhaustion.
- **PydanticAI Test Suite**: Decoupled `tests/integration/test_pydantic_ai_pipeline.py` from ChromaDB mocks; updated tests to verify deterministic exact match and unknown concept fallback.
- **CI Workflow Configuration**: Removed obsolete `GOALCOACH_ENABLE_VECTOR_RETRIEVAL: "true"` environment variable from `.github/workflows/ci.yml`.


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
