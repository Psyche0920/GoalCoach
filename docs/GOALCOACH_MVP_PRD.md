# GoalCoach — MVP Technical Product Requirements Document (PRD)

**Document Status:** Approved Core Baseline

**Target Stage:** Agentic AI MVP

**Curriculum Scope:** HSK 1

**System Topology:** Closed State-Driven Agentic Learning System

---

## 1. Executive Goal & Invariants

GoalCoach is an adaptive learning system, not an open-ended conversational chatterbot. Every learner interaction mutates persistent state, and that updated state directly determines future planning and pedagogical interventions.

```mermaid
flowchart LR
    Goal["Goal Definition"] --> Plan["Adaptive Planning"]
    Plan --> Teach["Targeted Teaching"]
    Teach --> Grade["Rubric Grading"]
    Grade --> Progress["Progress Update"]
    Progress --> Persist[("Persist State (SQLite)")]
    Persist --> Replan{"Adapt / Re-Plan?"}
    Replan -- Yes --> Plan
    Replan -- No --> Teach

```

### Core Axioms

* **Core Success Criterion:** **Same goal + different learner state $\rightarrow$ different plan**.


* **No Unbounded Memory:** Conversational history does not represent student mastery; only deterministic database records drive progression.


* **System-Directed Learning:** The system actively drives review, remediation, and concept pacing rather than asking the user what they want to study.



---

## 2. Core Design Principles

1. **Agents Exclusively for Non-Deterministic Decisions:** Use PydanticAI reasoning agents strictly when open-ended contextual judgment is required (planning curriculum sequences and adapting instructional tactics).


2. **Deterministic Governance:** Event routing, state persistence, mastery mutations, retention decay calculations, prerequisite checks, and format validation remain 100% deterministic Python code.


3. **Event-Driven Architecture:** Interactions trigger explicit event dispatches; sequential multi-agent chains (e.g., Planner $\rightarrow$ Retrieval $\rightarrow$ Tutor $\rightarrow$ Grader $\rightarrow$ Progress) for a single interaction are strictly prohibited.


4. **Persistent State as Single Source of Truth:** The `LearnerState` stored in SQLite is authoritative.


5. **Curriculum-Bounded Operation:** The curriculum defines the upper bound of what can be taught; agents operate strictly within verified curriculum boundaries.


6. **Zero Heavy Vector DB Overload:** Vector search and external Vector DB (ChromaDB) are completely decommissioned; all concept and curriculum lookups execute deterministically via `ContentService` querying SQLite Database #1.



---

## 3. High-Level Architecture

The platform separates fast learner-facing response paths from state evaluation:

```mermaid
flowchart TD
    User([Learner Event]) --> Orch["Deterministic Orchestrator"]
    
    Orch -- "GOAL_CREATED / needs_replanning" --> PlanAgent["Planning Agent (PydanticAI)"]
    Orch -- "HELP_REQUESTED / SESSION_STARTED" --> TeachAgent["Teaching Agent (PydanticAI)"]
    Orch -- "ANSWER_SUBMITTED" --> Grader["Grader Component (LLM Evaluator)"]
    
    PlanAgent --> PlanUp["PlanUpdate (Pydantic Schema)"]
    PlanUp --> DB[("SQLite Database #2 (WAL Mode)")]
    
    TeachAgent --> Action["TeachingAction (Pydantic Schema)"]
    Action --> User
    
    Grader --> GradeRes["GradingResult (Strict Rubric)"]
    GradeRes --> ProgServ["Progress Service (Deterministic)"]
    ProgServ --> DB
    
    DB -. "State Updates / needs_replanning=True" .-> Orch

```

---

## 4. System Components & Responsibilities

| Component | Classification | Core Responsibility |
| --- | --- | --- |
| **Deterministic Orchestrator** | Pure Python Logic | Evaluates incoming events and routes them to the appropriate worker without invoking an LLM.|
| **Planning Agent** | PydanticAI Agent | Decides **what** the learner should do next based on goals, time budget, and historical weaknesses.|
| **Teaching Agent** | PydanticAI Agent | Decides **how** to teach the current concept right now based on past failed explanations and active error tags.|
| **Grader Component** | Stateless LLM Evaluator | Evaluates freeform answers against predefined rubric standards and gating conditions.|
| **Progress Service** | Deterministic Engine | Calculates retention decay, mastery deltas, mistake logging, and review schedules.|
| **Content Service** | Deterministic Engine | Provides sub-millisecond querying of concepts, examples, and prerequisite relations from Database #1.|
| **Repository Layer** | SQLAlchemy / aiosqlite | Encapsulates read/write operations for relational and serialized JSON domain states.|
| **SQLite DBs** | Relational Persistence | DB #1: Static HSK1 Curriculum. DB #2: Dynamic `LearnerState` in WAL mode.|

---

## 5. Event Routing Lifecycle

The Deterministic Orchestrator handles all incoming requests through an explicit priority map:

```mermaid
stateDiagram-v2
    [*] --> EventReceived: Inbound Event
    
    state EventReceived {
        [*] --> CheckEvent
        CheckEvent --> Planning: GOAL_CREATED
        CheckEvent --> Teaching: HELP_REQUESTED
        CheckEvent --> CurrentPlan: SESSION_STARTED
        CheckEvent --> Grading: ANSWER_SUBMITTED
    }

    Planning --> PlanningAgent: Invoke Planner
    PlanningAgent --> MutatePlan: Emit PlanUpdate
    MutatePlan --> SaveState: Persist to SQLite

    Teaching --> TeachingAgent: Invoke Tutor
    TeachingAgent --> EmitAction: Emit TeachingAction
    EmitAction --> ReturnClient: Send to User

    CurrentPlan --> ActiveCheck: Plan Valid?
    ActiveCheck --> TeachingAgent: Yes (Continue Lesson)
    ActiveCheck --> PlanningAgent: No (Regenerate Plan)

    Grading --> GraderLLM: Evaluate Answer
    GraderLLM --> ProgressService: Emit GradingResult
    ProgressService --> SaveState: Update Mastery & Retention
    SaveState --> ReplanningGate: Check needs_replanning Flag
    
    ReplanningGate --> PlanningAgent: True (Re-allocate Budget)
    ReplanningGate --> [*]: False (Turn Closed)

```

* **`needs_replanning` Lifecycle:** A state boolean flag, not an event. When the Progress Service flags repeated errors on the same concept, it sets `needs_replanning = True`. The Orchestrator intercepts this state and calls the Planning Agent to re-allocate today's session budget.


* **`HELP_REQUESTED` Context:** Emitted when a student indicates confusion (e.g., clicks "Coach Help" or inputs *"I don't get it"*). The Teaching Agent evaluates previous failed attempts and switches pedagogical strategies.



---

## 6. Curriculum / Teaching Materials Database

The Teaching Materials Database (Database #1: `goalcoach_hsk1_learning.db`) is the canonical, grounded knowledge source:

* **Concepts:** Concept IDs, canonical names, semantic definitions, level tags.


* **Reviewed Examples:** Bilingual character pairings with accurate Pinyin and audio markers.


* **Prerequisites:** Dependency graph mapping foundations to downstream rules.



```mermaid
graph TD
    subgraph Database_1 ["Database #1: Static Curriculum"]
        C1["Prerequisite Concept A"] -->|Prerequisite Edge| C2["Target Concept B"]
        C2 --- E1["Reviewed Example 1"]
        C2 --- E2["Reviewed Example 2"]
        C2 --- TC["Canonical Teaching Card"]
    end
    
    subgraph Agent_Access ["Deterministic Tool Access"]
        ContentService["Content Service"] --> C2
        ContentService --> E1
        ContentService --> TC
    end

    ContentService -.->|get_concept / get_examples| PlanAgent["Planning Agent"]
    ContentService -.->|get_concept / get_examples| TeachAgent["Teaching Agent"]

```

* **Relational Over Vector:** Because HSK1 contains 20 concepts, 21 cards, and 18 prerequisites, all lookups execute deterministically via SQL in $<1\text{ ms}$ without vector drift or embedding overhead.


* **Soft Prerequisites:** Prerequisites serve as **planning signals, not hard UI locks**. The Planning Agent may schedule prerequisite reinforcement without restricting free exploration.



---

## 7. Planning Agent Specification

**Core Question:** *"Given the current learner state and curriculum graph, what should the student do next?"*

```mermaid
flowchart LR
    subgraph Inputs ["Planning Inputs"]
        G["Goal & Time Budget"]
        M["Mastery & Decay"]
        E["Error Profile History"]
        C["Curriculum & Pre-reqs"]
    end
    
    Inputs --> PA["Planning Agent (PydanticAI)"]
    
    PA --> Decisions{"Reasoning Engine"}
    Decisions --> D1["Continue Sequence"]
    Decisions --> D2["Remediate Concept"]
    Decisions --> D3["Reinforce Prerequisite"]
    Decisions --> D4["Postpone Topic"]
    
    Decisions --> Output["PlanUpdate (Strict Schema)"]

```

### Structured Output Schema: `PlanUpdate`

* `daily_allocation_minutes`: Total session duration (e.g., 20).


* `ordered_items`: Ordered list of tasks categorized into `REVIEW`, `REMEDIAL`, or `NEW`.


* `adaptation_rationale`: Transparent explanation of why this plan was selected.


* `roadmap_adjustments`: Concrete mutations applied to the student's macro roadmap.



### Execution Guardrails

* All emitted concept IDs are validated deterministically against Database #1 before persistence.


* Cumulative item durations must not exceed the student's active time budget.


* Failed schema validations trigger an automated PydanticAI repair loop without polluting application state.



---

## 8. Adaptive Roadmap & DailyPlan Modeling

The Roadmap provides a macro view of the curriculum, while the `DailyPlan` executes the immediate learning queue.

```mermaid
flowchart TD
    subgraph Standard_Path ["Standard Daily Plan Flow"]
        SP1["5m: Review (hsk1_like)"] --> SP2["8m: Remedial (hsk1_modal_hui)"]
        SP2 --> SP3["7m: New (hsk1_what)"]
    end

    subgraph Adapted_Path ["Adapted Plan (After Repeated Failure)"]
        AP1["5m: Review (hsk1_like)"] --> AP2["10m: Targeted Remedial (hsk1_modal_hui)"]
        AP2 --> AP3["5m: Diagnostic Item (hsk1_modal_hui vs neng)"]
        AP3 -.-> Postponed["New Topic (hsk1_what) -> POSTPONED"]
    end

    Standard_Path ==>|Repeated Confusion Detected| Adapted_Path

```

---

## 9. Teaching Agent Specification

**Core Question:** *"Given the active concept, learner error history, and failed attempts, how should we teach right now?"*

```mermaid
flowchart TD
    subgraph Context_Window ["Contextual Inputs"]
        C["Active Concept Card"]
        E["Recurring Error Codes"]
        H["Previous Failed Explanations"]
        I["Interests (e.g., Travel)"]
    end

    Context_Window --> TA["Teaching Agent"]
    
    TA --> Loop{"Reasoning Cycle"}
    Loop --> Action["Emit TeachingAction"]

    subgraph Action_Kinds ["TeachingAction Modalities"]
        A1["EXPLANATION"]
        A2["HINT"]
        A3["CONTRAST_EXAMPLE"]
        A4["EXERCISE"]
        A5["DIALOGUE"]
        A6["RETRY"]
    end

    Action --> Action_Kinds
    Action_Kinds --> UserResponse([Learner Responds])
    UserResponse -. "Triggers Next Interaction Event" .-> TA

```

### Structured Output Schema: `TeachingAction`

* `action_kind`: Tag matching the pedagogical mode chosen (`EXPLANATION`, `HINT`, etc.).


* `concept_id`: Canonical curriculum tag being exercised.


* `content`: Bilingual explanation or instructional dialogue formatted with Pinyin.


* `pinyin`: Disambiguated tone readings for Hanzi characters.


* `exercise_payload`: Structured payload if the action presents an assessable problem.



---

## 10. Grader Component Specification

The Grader is an **isolated LLM evaluator, not an autonomous agent**. It assesses freeform user submissions against predefined rubric dimensions.

```mermaid
flowchart LR
    Submission["Learner Submission"] --> Match{"Deterministic Match?"}
    Match -- Yes (accepted_answers) --> FastPass["Pass: 1.0 (Bypass LLM)"]
    
    Match -- No --> LLMGrader["Grader LLM Component"]
    
    subgraph Rubric_Axes ["3-Axis Evaluation"]
        LLMGrader --- R1["Grammatical Correctness (Syntax/Particles)"]
        LLMGrader --- R2["Semantic Precision (Task Fulfillment)"]
        LLMGrader --- R3["Pragmatic Appropriateness (Register)"]
    end
    
    Rubric_Axes --> Eval{"Score >= Pass Threshold?"}
    Eval -- Yes --> Pass["passed_gates = True"]
    Eval -- No --> Fail["passed_gates = False"]
    
    Pass --> Result["GradingResult"]
    Fail --> Result

```

### Contract: `GradingResult`

* `passed_gates`: Boolean indicating whether core rubric minimums were satisfied.


* `scores`: Explicit float scores across evaluated axes ($[0.0, 1.0]$).


* `detected_errors`: List of standardized taxonomy codes (e.g., `ERR_QUESTION_MA`, `ERR_WORD_ORDER`).


* `feedback`: Targeted, factual feedback addressing the learner's specific mistake.


* *Note:* The Grader never calculates mastery; it only produces grading evidence.



---

## 11. Deterministic Progress Service

The Progress Service executes the mathematical transitions converting evaluation evidence into state updates:

```mermaid
sequenceDiagram
    autonumber
    participant G as Grader Component
    participant P as Progress Service
    participant S as Persistent LearnerState
    participant O as Orchestrator

    G->>P: Emit GradingResult
    activate P
    P->>P: Record attempt count & timestamp
    alt passed_gates == True
        P->>P: Concept Mastery: max(0.0, min(1.0, Score + 0.25))
        P->>P: Extend Spaced Interval: Interval * 1.8
        P->>P: Reset Retention: R = 1.0
    else passed_gates == False
        P->>P: Concept Mastery: max(0.0, min(1.0, Score - 0.10))
        P->>P: Reset Spaced Interval: Interval = 1.0
        P->>P: Append error code to error_profile
    end
    P->>P: Compute Decay: R(t) = R_0 * exp(-lambda * delta_t)
    P->>P: Check repeated error thresholds
    opt Error occurrences >= 2
        P->>P: Set needs_replanning = True
    end
    P->>S: Save updated state via Repository (SQLite WAL)
    deactivate P
    S-->>O: Read updated state
    opt needs_replanning == True
        O->>O: Trigger Planning Agent (Budget Re-allocation)
    end

```

---

## 12. Persistent Learner State & Data Hierarchy

Persistent state is stored exclusively in **SQLite Database #2 (`goalcoach.db`) with WAL mode enabled**.

```mermaid
erDiagram
    LEARNER_STATE ||--o| LEARNING_GOAL : contains
    LEARNER_STATE ||--o{ CONCEPT_MASTERY : tracks
    LEARNER_STATE ||--o{ ERROR_RECORD : logs
    LEARNER_STATE ||--o| DAILY_PLAN : maintains
    LEARNER_STATE ||--o{ SESSION_SUMMARY : archives

    LEARNER_STATE {
        UUID learner_id PK
        boolean needs_replanning
        datetime updated_at
    }
    LEARNING_GOAL {
        string title
        int target_hsk_level
        int daily_available_minutes
    }
    CONCEPT_MASTERY {
        string concept_id PK
        float mastery_score
        float retention_score
        datetime next_review_at
    }
    ERROR_RECORD {
        string code PK
        string concept_id
        int occurrences
    }
    DAILY_PLAN {
        string status
        json items
    }

```

---

## 13. Service & Tool Access Pattern

Agents never communicate with external storage or execution environments directly; they interact through structured tool definitions:

```mermaid
flowchart LR
    Agent["PydanticAI Agent"] -->|Typed Call| Tool["Agent Tool Decorator"]
    Tool -->|Execute| Service["Deterministic Service"]
    Service -->|Query / Mutate| Repo["Repository Layer"]
    Repo -->|SQL / Pragma| DB[("SQLite Database")]

```

* **Agent Layer:** Houses reasoning logic, prompts, and output schema definitions.


* **Tool Layer:** Exposes typed function signatures with docstrings to guide model selection.


* **Service Layer:** Houses deterministic business rules (calculating progress and validating prerequisites).


* **Repository Layer:** Manages database sessions, connection pooling, and JSON column serialization.



---

## 14. Deterministic Content Service

The Content Service acts as the grounded gatekeeper for curriculum materials, replacing vector retrieval:

```mermaid
flowchart TD
    TA["Teaching / Planning Agent"] -->|Tool Call| CS["Content Service"]
    
    subgraph Content_Operations ["Deterministic Access Routes"]
        CS --> F1["get_concept(concept_id)"]
        CS --> F2["get_examples(concept_id)"]
        CS --> F3["get_prerequisites(concept_id)"]
        CS --> F4["list_all_concepts()"]
    end

    Content_Operations --> Repo["ContentRepository (SQLAlchemy)"]
    Repo --> DB1[("Database #1: goalcoach_hsk1_learning.db")]

```

---

## 15. End-to-End Walkthrough

```mermaid
sequenceDiagram
    autonumber
    actor Learner
    participant UI as Client Interface
    participant O as Orchestrator
    participant PA as Planning Agent
    participant TA as Teaching Agent
    participant GC as Grader Component
    participant PS as Progress Service
    participant DB as SQLite DB #2

    Learner->>UI: Defines HSK1 Goal (20 min/day, Travel)
    UI->>O: Event: GOAL_CREATED
    O->>PA: Call Planner with Goal Context
    PA->>DB: Read LearnerState & Pre-reqs
    PA-->>O: Emit PlanUpdate (Allocates 20 min)
    O->>DB: Save DailyPlan (Status: ACTIVE)
    
    Learner->>UI: Start Practice
    UI->>O: Event: SESSION_STARTED
    O->>TA: Call Tutor for Active Item (e.g., 会 / 能)
    TA-->>UI: Emit TeachingAction (EXPLANATION + Travel Dialogue)
    
    Learner->>UI: Submits Answer
    UI->>O: Event: ANSWER_SUBMITTED
    O->>GC: Grade Answer against Rubric
    GC-->>PS: Return GradingResult (failed_gates: ERR_MODAL_HUI)
    PS->>DB: Decrement Mastery, Log Error Code
    PS->>DB: Repeated Error >= 2 -> Set needs_replanning = True
    
    O->>DB: Inspect Latest State
    opt needs_replanning is True
        O->>PA: Trigger Adaptive Re-Plan
        PA-->>O: Emit PlanUpdate (Postpones new topic, slots diagnostic remediation)
        O->>DB: Persist Adapted DailyPlan
    end
    O-->>UI: Next Action Directed to Learner

```

---

## 16. MVP Acceptance Criteria (100% Verified)

* [x] **AC1 — Closed Loop State Mutation:** User interactions successfully mutate persistent state records in SQLite (`tests/integration/test_closed_loop.py::test_ac1_ac7_closed_loop_state_mutation_and_durability`).
* [x] **AC2 — State-Conditioned Adaptation:** State changes dynamically alter subsequent planning allocations or instructional strategies (`tests/integration/test_closed_loop.py::test_ac2_ac10_core_planning_proof_same_goal_different_state`).
* [x] **AC3 — Structured Planning:** The Planning Agent outputs schema-validated `PlanUpdate` payloads.
* [x] **AC4 — Adaptive Strategy Switching:** The Teaching Agent selects alternative modalities (e.g., switching from explanation to contrast examples) when previous attempts fail (`tests/integration/test_closed_loop.py::test_ac4_ac11_core_teaching_proof_adaptive_strategy_switching`).
* [x] **AC5 — Rubric Enforcement:** The Grader evaluates submissions against predefined rubric standards and pass thresholds (`tests/integration/test_closed_loop.py::test_ac5_grader_fast_path_and_rubric`).
* [x] **AC6 — Deterministic Progress:** All progress calculations, retention decays, and mastery adjustments are executed by deterministic code (`tests/integration/test_closed_loop.py::test_ac6_progress_service_mathematical_invariants`).
* [x] **AC7 — Relational Persistence:** All learner data survives application restarts via SQLite WAL storage (`tests/integration/test_closed_loop.py::test_ac1_ac7_closed_loop_state_mutation_and_durability`).
* [x] **AC8 — Chain Elimination:** No sequential multi-agent LLM chain runs for a single user turn (`tests/integration/test_closed_loop.py::test_ac8_zero_sequential_agent_chaining`).
* [x] **AC9 — Observable Plan Shifts:** Agent decisions produce measurable changes in the daily task queue.
* [x] **AC10 — Core Planning Proof:** **Same goal + different learner state $\rightarrow$ different plan** (`tests/integration/test_closed_loop.py::test_ac2_ac10_core_planning_proof_same_goal_different_state`).
* [x] **AC11 — Core Teaching Proof:** **Same concept + different error history $\rightarrow$ different instructional action** (`tests/integration/test_closed_loop.py::test_ac4_ac11_core_teaching_proof_adaptive_strategy_switching`).

### Remediation Engine Invariants (Stress-Tested)
- **Anti-Stagnation Guarantee:** Remedial exercise rotation ensures that a learner never loops endlessly on the same exercise ID (`test_remediation_exercise_rotates_and_does_not_repeat_e01`).
- **Prerequisite DAG Unlocking:** Remediating an upstream blocking concept immediately unlocks downstream unready concepts (`test_edge_case_prerequisite_dag_blocks_unready_and_unlocks_remediated`).
- **Error Profile Resolution:** Successful remediation purges resolved errors from `error_profile` and resets `needs_replanning` without Pydantic schema validation failures (`test_remediation_success_clears_error_profile_and_resets_replanning`).



---

## 17. Telemetry & Observability

To maintain engineering visibility, the system records the following structured parameters for every agent execution:

```mermaid
flowchart LR
    Trace["Execution Event"] --> M1["Input / Output Schemas"]
    Trace --> M2["Tool Call Traces"]
    Trace --> M3["Pydantic Validation Latencies"]
    Trace --> M4["State Diffs (Mastery & Retention)"]
    Trace --> M5["Token Consumption & Cost (OpenRouter)"]
    Trace --> M6["Active Model & Prompt Hashes"]

```

---

## 18. Deferred Implementation Items (TBD)

* Exact mathematical retention decay constant $\lambda$ and spaced multiplier parameters.


* Production rubric weighting across grammatical, semantic, and pragmatic axes.


* Final grading pass threshold values.


* Session conversation transcript retention policy and pruning strategy.


* Expansion of curriculum content past HSK1.