# Working-Tree Diff from Latest GitHub `main`

This is a concise inventory of what the current working tree changes relative
to the latest GitHub `origin/main` branch (`8cad922`, `docs(changelog):
document v0.1.2 bloat removal, API consolidation, and frontend alignment`).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The comparison includes committed work on `wehan` plus the current uncommitted
cleanup. It covers 18 added files, 53 modified files, and 41 removed files.
The current branch is ahead of `origin/main` by 4 commits and behind by 16.

## [Unreleased] - 2026-09-22

## Added / Restored

- **Goal-Scoped Learning Loop** (`apps/api`, `apps/web`): Connected goal creation, Planning Agent
  roadmap selection, Teaching Agent sessions, grading, progress updates, and
  targeted replanning into one backend-driven loop. The frontend now consumes
  authoritative API state instead of maintaining a separate curriculum or
  planning engine.
- **Persisted Agent Roadmap** (`src/goalcoach/domain/models.py`, `orchestrator.py`): Added goal-bound `roadmap_concept_ids`,
  adjustments, coverage rationale, and schema version to `LearnerState`.
  Daily replanning preserves the Agent-selected roadmap and changes only the
  budget-bounded daily plan.
- **Strict Planning Output Contract** (`planning_agent.py`): Added `AgentPlanUpdate` as the
  model-facing schema for the Planning Agent. Roadmap IDs and coverage
  rationale are required at structured-output time; the persisted
  `PlanUpdate` keeps backward-compatible defaults.
- **Bounded Cross-Session History** (`agent_history.py`, `domain/models.py`): Added active-session
  state, teaching-turn summaries, and bounded Agent context so Planning and
  Teaching use compact persisted learning evidence rather than long raw
  transcripts.
- **Learner State Versioning** (`repositories.py`, `database.py`): Added state-version checks
  and atomic `save_with_event()` persistence for answer events.
  Conflicting concurrent updates now return HTTP 409 instead of silently
  overwriting learner state.
- **Versioned Read Router** (`apps/api/routes/learning.py`): Restored a typed
  read router with `/api/v1/learners/{id}`, `/today-plan`, `/roadmap`, and
  curriculum endpoints. GitHub `main` keeps all reads and mutations in one
  router and includes direct completion/chat routes; this tree keeps the
  event gateway as the sole mutation boundary.
- **Focused Teaching Modal** (`TeachingAgentModal.tsx`): Replaced the large prototype UI set with a
  focused Teaching Agent modal supporting explanations, exercises, help
  requests, grading results, and replanning notices.
- **Roadmap Projection View** (`RoadmapView.tsx`): Added a goal-coverage view rendered directly
  from the persisted Planning Agent roadmap and daily-plan items.
- **Structured Model Telemetry** (`telemetry/__init__.py`, `pydantic_ai_models.py`): Added privacy-safe component, provider,
  latency, token, validation, and fallback telemetry for PydanticAI calls.
- **Deterministic Test Doubles** (`tests/fakes.py`): Added shared fake Planning, Teaching, and
  Grading workers for offline API and closed-loop integration tests.

## Changed

- **Focused Frontend Architecture** (`apps/web/src`): Replaced GitHub `main`'s remaining
  client-side curriculum, pinyin engines, planners, graders, progress reducer,
  and direct concept-completion endpoint usage with the FastAPI-driven React
  application. The SPA now focuses on daily plan, roadmap, retention,
  profile, and Teaching Agent flows through canonical learning events.
- **Restored Deterministic Progress Reducer** (`application/progress_reducer.py`): GitHub
  `main` removed this module and inlined progress calculation in its router.
  This tree restores it as the authoritative reducer, introduces binary
  `exposed`, and keeps established API names as compatibility projections.
  `learned_percent`, `course_coverage`, `learned_progress`, and
  `communication_outcome_percent` map to Exposure; `mastered_progress` reports
  retained mastery (`mastery_score × current retention`); and
  `mastered_concept_rate` remains the locked Mastery gate ratio.
- **Updated Goal Completion Formula**: Changed the top-level metric to
  `0.4 × exposure_rate + 0.6 × retained_mastery`, so it reflects current
  roadmap knowledge and memory retention without double-counting output
  evidence.
- **Strengthened Roadmap Guardrails**: Planning now validates complete,
  curriculum-grounded roadmaps, minimum goal coverage, roadmap stability on
  daily replans, daily-item membership, time budget, and remediation
  priority.
- **Improved LLM Resilience** (`pydantic_ai_models.py`): Added transient transport/provider
  retries for OpenRouter and optional Ollama fallback, while preserving
  deterministic behavior when LLM execution is disabled.
- **Simplified Runtime Configuration** (`config.py`, `.env.example`): Removed weekly cost,
  background update, vector, and LangGraph flags from GitHub `main`; added an
  explicit `GOALCOACH_ENABLE_PREREQUISITES=false` runtime setting.
- **Tightened Learning Evidence**: Only the first completion of the current
  planned item is progress-eligible. Roadmap review and repeated attempts
  return feedback without changing progress, mastery, or study time.
- **Refined Remediation State**: Separated the scheduling threshold from the
  lifelong error profile; successful remediation clears the active threshold
  but never erases historical errors.
- **Expanded Orchestrator Event Semantics** (`orchestrator.py`): Added roadmap stability,
  learner-local daily-plan expiry, progress-eligibility rules, and explicit
  `REPLAN_REQUESTED`. Responses consistently
  include state, progress summary, next action, daily plan, agent outputs,
  and user-facing notices.
- **Correlated API Requests**: Added request ID middleware and structured
  agent telemetry correlation.
- **Superseded GitHub `main` Cleanup**: GitHub `main` had already consolidated
  the API and removed large legacy modules in release `0.1.2`. This branch
  moves further by reintroducing only typed read projections, replacing
  direct mutation endpoints with lifecycle events, and keeping roadmap,
  session history, and progress in one authoritative aggregate.
- **Removed Files vs GitHub `main`** (41 files): Deleted remaining pinyin and
  prototype components, frontend curriculum/audio data, local progress logic,
  chat/completion mutation routes, retrieval tools, PydanticAI pipeline tests,
  config tests, and the code-reviewer agent definition. Also removed the
  standalone Slidev project, empty root package lock, and obsolete scripts
  package in the uncommitted cleanup.

## Removed

- **Remaining Frontend Prototype Stack**: Standalone pinyin charts,
  flashcards, quizzes, knowledge tree, mastery dashboard, study-session and
  chat drawers, local curriculum data, local progress logic, and audio/RAG
  utilities still present on GitHub `main`.
- **Direct Completion Mutation**: Removed
  `POST /learners/{id}/complete-concept`; completion evidence is now produced
  only through `ANSWER_SUBMITTED` and the durable learning event boundary.
- **Prototype Conversation Endpoint**: Removed `POST /tutoring/chat` and the
  duplicated non-versioned learner endpoints retained on GitHub `main`.

## Fixed / Behavior Differences

- **Roadmap Generation Failures**: Prevented the model from silently omitting
  required roadmap fields by making the Agent-facing schema explicit. Real
  provider verification produced varied roadmap lengths (12–20 concepts in
  the verification run), confirming the minimum-eight rule is not a fixed
  target.
- **Misleading LLM Error Boundary**: Distinguished provider availability from
  model output-validation failures and preserved structured diagnostics in
  API responses where available.
- **Roadmap/Progress Drift**: Persisted roadmap identity with the learner
  state and rebuilt roadmap and progress projections from the same backend
  state.
- **Concurrent Answer Submission**: Added atomic event/state persistence and
  optimistic conflict handling. The frontend refreshes authoritative state and
  retries a stale request once; lifecycle conflicts still require a fresh
  teaching turn.
- **Remediation Loop Stability**: Aligned remediation replanning with roadmap
  preservation, exercised rotation, prerequisite gating, and stale-plan
  detection to avoid repeated rebuild cycles.
- **Legacy State Migration**: Added SQLite schema migration and JSON
  backfill for learner states that predate `state_version`.

### Security & Reliability

- Kept credentials in local `.env` and out of logs, prompts, telemetry, and
  repository history.
- Reduced concurrent-write risk with WAL mode, bounded SQLite busy timeout,
  version checks, and atomic transactional event persistence.
- Added explicit API failure contracts for model unavailability and invalid
  Agent output.

### Verification

- `73 passed`: fast unit and API suites.
- `ruff check src apps tests`: passed.
- `ruff format --check` on the current feature-relevant files: passed.
- `npm --prefix apps/web run lint` / TypeScript build check: passed.
- Real OpenRouter Planning Agent smoke tests: six consecutive successful
  goal-created responses with Agent-authored roadmaps.
