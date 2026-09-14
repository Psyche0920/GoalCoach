# MISSION: Transform GoalCoach into a Closed State-Driven Agentic System (MVP PRD)

## Architectural Ground Rules
1. Zero Sequential Multi-Agent Pipelines: Never run Planner -> Grader -> Teacher in a single chain.
2. Agents Only for Non-Deterministic Reasoning: Use PydanticAI agents exclusively for Planning (what to study) and Teaching (how to teach). The Grader is an LLM component (no agent loops). Orchestrator, Progress Service, and Content Service are deterministic Python code.
3. No Vector DB Required: Deprecate vector retrieval dependencies for the MVP. Use ContentService against Database #1 (SQLite) for grounded concept and prerequisite lookup.
4. Single Source of Truth: SQLite Database #2 (`goalcoach.db` with WAL mode) stores LearnerState. All agent and grading outputs mutate or read from this state.

---

### PHASE 1: Domain Contracts & Schema Harmonization
- Target Files:
  - `src/goalcoach/domain/enums.py`
  - `src/goalcoach/domain/models.py`
  - `src/goalcoach/domain/events.py`

- Deliverables:
  1. Define Event Enums: `GOAL_CREATED`, `SESSION_STARTED`, `HELP_REQUESTED`, `ANSWER_SUBMITTED`.
  2. Define `TeachingActionKind`: `EXPLANATION`, `RETRY`, `HINT`, `CONTRAST_EXAMPLE`, `EXERCISE`, `DIALOGUE`, `FREEFORM`.
  3. Define `TeachingAction` (Pydantic v2):
     - `action_kind`: TeachingActionKind
     - `concept_id`: str
     - `content`: str (Bilingual explanation/dialogue with Pinyin)
     - `pinyin`: str | None
     - `exercise_payload`: dict[str, Any] | None (if presenting practice)
  4. Define `PlanUpdate` (Pydantic v2):
     - `daily_allocation_minutes`: int
     - `ordered_items`: list[PlanItem] (REVIEW, REMEDIAL, NEW)
     - `adaptation_rationale`: str
     - `roadmap_adjustments`: list[str]
  5. Update `LearnerState`:
     - Add `needs_replanning: bool = False`
     - Add `context_interests: list[str] = Field(default_factory=list)` (e.g., travel, business)
     - Ensure existing `mastery`, `error_profile`, and `active_plan` are intact.

---

### PHASE 2: Deterministic Foundations (Content, Persistence, Progress)
- Target Files:
  - `src/goalcoach/infrastructure/persistence/content_service.py`
  - `src/goalcoach/infrastructure/persistence/learner_repository.py`
  - `src/goalcoach/application/progress_service.py`
  - `src/goalcoach/application/orchestrator.py`

- Deliverables:
  1. `ContentService`: Expose deterministic synchronous methods wrapped over SQLite `ContentRepository`:
     - `get_concept(concept_id: str) -> Concept | None`
     - `get_examples(concept_id: str) -> list[Example]`
     - `get_prerequisites(concept_id: str) -> list[str]`
     - `list_all_concepts() -> list[Concept]`
  2. `SqliteLearnerRepository`: Implement async get/save operations for `LearnerState` to `goalcoach.db` using WAL mode.
  3. `ProgressService`: Implement deterministic state mutation:
     - `apply_grading_result(state: LearnerState, result: GradingResult) -> LearnerState`:
       - On Pass: increment concept mastery (+0.25), decay retention curve, advance review interval.
       - On Fail: decrement concept mastery (-0.10), log error code to `error_profile`.
       - Evaluate repeated errors: if same error occurrence >= 2, set `state.needs_replanning = True`.
  4. `DeterministicOrchestrator`: Implement event dispatcher:
     - `handle_event(event_type: EventType, payload: dict, state: LearnerState)` routing cleanly between Planning Agent, Teaching Agent, and Grader.

---

### PHASE 3: The 3 LLM Workers (PydanticAI)
- Target Files:
  - `src/goalcoach/agents/planning_agent.py`
  - `src/goalcoach/agents/teaching_agent.py`
  - `src/goalcoach/agents/grader_component.py`
  - `src/goalcoach/infrastructure/llm/pydantic_ai_models.py`

- Deliverables:
  1. Failover LLM Runner: `run_with_fallback()` toggling between OpenRouter (`Qwen-2.5-72B-Instruct`) and local Ollama (`unsloth/gemma-4-12b-it-GGUF`).
  2. `planning_agent`:
     - System prompt: Reason over learner goals, target date, available minutes, weaknesses, and prerequisites.
     - Tools: `content_service.list_all_concepts`, `content_service.get_prerequisites`.
     - Output: `PlanUpdate`.
  3. `teaching_agent`:
     - System prompt: Zone of Proximal Development tutor. Adapt explanation style based on previous failures and active error codes.
     - Tools: `content_service.get_concept`, `content_service.get_examples`.
     - Output: `TeachingAction`.
  4. `grader_component`:
     - Stateless evaluation function using PydanticAI with `result_type=GradingResult`.
     - Evaluate grammar, task achievement, and particle usage (吗, 呢, 了). Fast-path match for exact reference answers.

---

### PHASE 4: Terminal Prototype & FastAPI Event Wiring
- Target Files:
  - `teaching_agent.py` (Terminal test harness using `rich.console`)
  - `apps/api/routes/learning_loop.py`
  - `apps/api/main.py`

- Deliverables:
  1. Terminal Harness (`teaching_agent.py`):
     - Interactive CLI loop running the full loop:
       Initialize state -> Planning Agent generates plan -> Teaching Agent emits TeachingAction -> User responds -> Grader scores -> Progress Service updates state -> Loop.
     - Render `rich.panel.Panel` for tutor output and `rich.table.Table` for mastery metrics.
  2. FastAPI Route `POST /api/v1/events`:
     - Accepts `{ event_type: str, learner_id: UUID, payload: dict }`.
     - Orchestrator loads state, dispatches event, updates state, and returns response JSON.

---

### PHASE 5: Verification & Core Behavioral Proof
- Target Files:
  - `tests/integration/test_closed_loop.py`

- Deliverables:
  1. Test AC1 & AC7: Assert answer submission persists updated mastery and error records to SQLite.
  2. Test AC2 & AC10 (The Core PRD Proof):
     - Create Learner A (Goal: HSK1, State: Clean).
     - Create Learner B (Goal: HSK1, State: Repeated error `ERR_QUESTION_MA`).
     - Run `PlanningAgent` for both. Assert Learner A gets new concepts while Learner B gets remedial practice on `hsk1_question_ma`.
  3. Test AC4 & AC11:
     - Run `TeachingAgent` on concept `hsk1_question_ma` with no previous error.
     - Run `TeachingAgent` on concept `hsk1_question_ma` with previous explanation failed.
     - Assert `TeachingAction` switches strategy (e.g., from EXPLANATION to CONTRAST_EXAMPLE/HINT).
  4. Code Quality: Ensure `ruff check` and `pytest tests/` pass with zero failures.