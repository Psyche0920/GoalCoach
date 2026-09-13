# GoalCoach --- MVP Technical PRD

**Stage:** Agentic AI MVP\
**Scope:** HSK1\
**System:** Closed State-Driven Agentic Learning System

## 1. Goal

GoalCoach is not a chatbot. Learner interactions update persistent
state, and the updated state changes future planning and teaching.

``` text
Goal → Plan → Teach → Grade → Progress Update → Persist State → Adapt / Re-plan ↺
```

**Core success criterion:** **Same goal + different learner state →
different plan.**

## 2. Design Principles

-   Use **Agents only for non-deterministic decisions**.
-   Keep routing, persistence, mastery/retention calculations, and
    validation deterministic.
-   Use an **event-driven** runtime, not a mandatory sequential
    multi-agent chain.
-   Persistent Learner State is the source of truth.
-   Curriculum defines what can be taught; Agents operate within that
    scope.
-   Retrieval is optional. No Retrieval Agent or Vector DB is required
    for the MVP.

## 3. Architecture

``` text
                    User / App Event
                           │
                           ▼
                Deterministic Orchestrator
                           │
          ┌────────────────┼────────────────┐
          │                │                │
     Plan / Re-plan    Teach / Help     Answer Submitted
          │                │                │
          ▼                ▼                ▼
   Planning Agent    Teaching Agent       Grader
          │                │                │
          │                ▼                ▼
          │         TeachingAction    GradingResult
          │                │                │
          │                ▼                ▼
          │              User       Progress Service
          │                                 │
          ▼                                 ▼
      PlanUpdate                Persistent Learner State
          │                                 │
          └────────────────┬────────────────┘
                           ▼
                     SQLite / SQLAlchemy
                           │
                           └──→ Latest State → Orchestrator ↺
```

## 4. Components

  -----------------------------------------------------------------------
  Component               Type                    Responsibility
  ----------------------- ----------------------- -----------------------
  Orchestrator            Deterministic code      Decide **when / who**
                                                  handles an event

  Planning Agent          Agent                   Decide **what the
                                                  learner should do
                                                  next**

  Teaching Agent          Agent                   Decide **how to teach
                                                  the current objective**

  Grader                  LLM component           Evaluate answers
                                                  against a predefined
                                                  rubric

  Progress Service        Deterministic service   Convert grading
                                                  evidence into
                                                  learner-state updates

  Content Service         Deterministic service   Retrieve grounded
                                                  curriculum content

  Repository              Data-access layer       Read/write persistent
                                                  data

  SQLite                  Database                Store learner state and
                                                  curriculum content
  -----------------------------------------------------------------------

## 5. Event Routing

``` text
GOAL_CREATED       → Planning Agent
SESSION_STARTED    → Current plan / Planning
HELP_REQUESTED     → Teaching Agent
ANSWER_SUBMITTED   → Grader → Progress Service → Persist State
```

The Orchestrator is **not an Agent or LLM planner**.

`needs_replanning` is a learner-state flag, not a user/app event. After a state update, the Orchestrator reads the latest state and invokes the Planning Agent when this flag indicates re-planning is needed.

A `HELP_REQUESTED` event is created when the learner actively asks for
help during a learning interaction, for example by using the existing
Coach/help interaction or entering a question such as *"I don't get it"*
or *"What's the difference?"*. The Teaching Agent then uses the current
concept, recent errors, and previous teaching attempts to choose a new
intervention.

## 6. Curriculum / Teaching Materials Database

**The Teaching Materials Database is the grounded knowledge source available to GoalCoach.**

Current scope: **HSK1**.

For the MVP, the Teaching Materials Database contains:

-   **Concepts** --- concept ID, definition/teaching notes, level
-   **Reviewed Examples** --- grounded examples linked to concepts
-   **Prerequisite relationships** --- dependencies between concepts

The database defines the available learning content but does **not** define a fixed learning sequence or Roadmap.

The **Planning Agent selects appropriate concepts from the Teaching Materials Database and organizes them into a personalized Roadmap** based on the learner's goal, current learner state, available study time, and concept relationships.

It does **not** prescribe teaching formats or store a fixed teaching flow.

The Teaching Agent dynamically decides the teaching strategy and
generates the required teaching material/action, such as:

-   Explanation
-   Retry
-   Hint
-   Contrast example
-   Exercise
-   Dialogue
-   Freeform interaction

Prerequisites are **planning signals, not hard locks**. The Planning
Agent may use them to decide whether to continue a concept, reinforce an
earlier concept, or re-plan the DailyPlan.


## 7. Planning Agent

**Question:** Given the learner state and curriculum constraints, **what
should happen next?**

### Inputs

-   Goal + target date
-   Available study time
-   Current Roadmap / DailyPlan
-   Mastery + retention
-   Due reviews + repeated errors
-   Curriculum concepts + prerequisites

### Decisions

-   Continue
-   Remediate
-   Pause / postpone
-   Reinforce prerequisite
-   Keep current plan

### Output

Structured `PlanUpdate`:

-   Daily allocation
-   Ordered PlanItems
-   Adaptation rationale
-   Roadmap changes when required

Example:

``` text
20 min
Review 喜欢        5 min
Remedial 会/能     8 min
New 什么           7 min
```

### Guardrails

The Agent makes the planning decision; deterministic code validates
execution:

-   Valid concept IDs
-   Prerequisite relationship validation
-   Time budget
-   Schema validation
-   Database transaction

**Schema validation** only ensures that Agent outputs follow the
expected structured data format and types before execution or
persistence. It does **not** make planning decisions.

## 8. Roadmap & DailyPlan

Roadmap and DailyPlan are the main user-visible Planning outputs.

The Roadmap represents the learner's current progression through the
supported curriculum. Prerequisites may inform Planning Agent decisions,
but the MVP does not require a separate hard-lock/unlock mechanism.

Example adaptation:

``` text
Before:
Review → Remedial → New

After repeated confusion:
Review → Remedial → Diagnostic Practice
New concept → Postponed
```

## 9. Teaching Agent

**Question:** Given the current learner context, **how should we teach
now?**

The Teaching Agent chooses both the **teaching strategy** and the
**material/action to present**.

### Inputs

-   Current PlanItem / Concept
-   Learner level + known vocabulary
-   Recent answers + error patterns
-   Previous explanations / teaching attempts
-   Interests / context
-   Grounded concepts and reviewed examples when needed

### Loop

``` text
Reason → Decide → Act → Observe ↺
```

Example:

``` text
Observation:
Repeated 会/能 confusion + previous explanation failed

Decision:
Simpler contrast + travel example + targeted diagnostic item
```

### Output: `TeachingAction`

Possible forms include:

-   Explanation
-   Retry
-   Hint
-   Contrast example
-   Exercise
-   Dialogue
-   Freeform interaction

The Teaching Agent may generate the required teaching material
dynamically, grounded in the supported curriculum.

The learner response becomes a new event.

### Tools

Examples:

``` text
get_concept()
get_examples()
get_recent_errors()
get_learner_state()
```

Retrieval is optional; it is not a separate Agent.

## 10. Grader

The Grader is an **LLM evaluation component, not an Agent**.

### Inputs

-   Exercise / prompt
-   Learner answer
-   Target concept
-   Rubric Standard
-   Allowed curriculum concept IDs

### Evaluation

The Grader must follow a predefined **Rubric Standard** and apply a
**Pass Threshold**.

``` text
Score ≥ Pass Threshold → PASS
Score < Pass Threshold → NOT PASS
```

-   Rubric Standard: **TBD**
-   Pass Threshold: **TBD**

### Output: `GradingResult`

-   Correctness / evaluation result
-   Error type
-   Affected concept ID
-   Confidence
-   Feedback facts

The Grader **does not calculate mastery**.

## 11. Progress Service

Deterministic code that converts grading evidence into Persistent
Learner State.

### Inputs

-   `GradingResult`
-   Current ConceptMastery
-   Existing error history
-   Review / attempt metadata

### Processing

``` text
Record attempt
→ Update evidence
→ Mastery / retention calculation
→ Update error counters
→ Update review date
→ Update state flags
```

### Output

`ProgressUpdate`, persisted through:

``` text
Progress Service → Repository → SQLAlchemy → SQLite
```

No Progress Agent is required.

## 12. Persistent Learner State

Long-term source of truth:

-   Goal
-   Roadmap
-   DailyPlan
-   Mastery
-   Errors
-   Attempts
-   Review schedule
-   Interests

Storage: **SQLite + SQLAlchemy**.

Agents access current state through controlled Tools rather than relying
on LLM conversation memory.

### Conversation Context

Recent dialogue and previous teaching attempts may help the Teaching
Agent understand what has already been tried.

Conversation Context is **not** the source of truth for mastery or
planning.

Persistence: **TBD**.

## 13. Tools / Services / Data

``` text
Agent → Tool → Service → Repository → SQLAlchemy / SQLite
```

-   **Agent:** reasons and decides.
-   **Tool:** Agent-callable function/capability.
-   **Service:** deterministic business logic.
-   **Repository:** data access.
-   **Database:** persistent truth.

Most MVP Tools can expose GoalCoach's own backend functions.

## 14. Content Service

Content Service provides deterministic access to grounded curriculum
content.

Typical functions:

``` text
get_concept()
get_examples()
get_prerequisites()
```

``` text
Agent → Tool → Content Service → Repository → Teaching Materials Database
```

Content Service is **not an Agent**.

## 15. End-to-End MVP Scenario

1. Learner sets an HSK1 goal, 20 min/day, with a travel context.
2. Planning Agent reads the goal, learner state, available concepts, and
   concept relationships, then generates an adaptive Roadmap and DailyPlan.
3. Learner reaches `会 / 能`.
4. Teaching Agent observes the current concept and learner context, then
   reasons about and generates an appropriate `TeachingAction`.
5. During the interaction, the learner may respond, ask a question, or
   request help. This creates a new user event such as `HELP_REQUESTED`.
6. Teaching Agent observes the current concept, learner state, recent
   errors, previous teaching attempts, and interaction context, then reasons
   about and decides the next `TeachingAction`.
   The action may be an explanation, retry, hint, contrast example,
   exercise, dialogue, freeform interaction, or another appropriate
   intervention.
7. When the learner submits an answer to an assessable interaction,
   the system creates an `ANSWER_SUBMITTED` event.
8. `ANSWER_SUBMITTED` → Orchestrator → Grader.
9. Grader evaluates the learner's answer using the predefined Rubric and
   Pass Threshold, producing a structured `GradingResult`, including any
   detected concept-level error.
10. Progress Service deterministically converts the `GradingResult` into
    learner-state updates and persists them.
11. Orchestrator reads the latest Persistent Learner State.
12. If the updated state indicates that re-planning is needed, the
    Orchestrator invokes the Planning Agent. The Planning Agent reasons over
    the new learner state and decides whether and how to adapt the remaining
    Roadmap / DailyPlan.
13. Subsequent Planning and Teaching decisions use the updated learner state,
    completing the closed state-driven loop.

## 16. MVP Acceptance Criteria

-   **AC1 --- Closed loop:** Learner answers can change Persistent
    Learner State.
-   **AC2 --- State-driven:** Changed state can change subsequent
    Planning or Teaching.
-   **AC3 --- Planning:** Planning Agent outputs structured DailyPlan /
    PlanUpdate.
-   **AC4 --- Adaptive teaching:** Teaching Agent can change strategy
    and generate a different TeachingAction based on learner context and
    interaction history.
-   **AC5 --- Rubric grading:** Grader follows a predefined Rubric +
    Pass Threshold.
-   **AC6 --- Deterministic progress:** Progress Service, not an Agent,
    updates mastery/error/review state.
-   **AC7 --- Persistence:** State persists in SQLite and is available
    to later interactions.
-   **AC8 --- No mandatory LLM chain:** No Planner → Retrieval Agent →
    Teaching Agent → Grader Agent → Progress Agent pipeline for every
    interaction.
-   **AC9 --- Visible adaptation:** Agent decisions produce observable
    plan or teaching changes.
-   **AC10 --- Core proof:** **Same goal + different learner state →
    different plan.**
-   **AC11 --- Teaching proof:** **Same concept + different learner
    context/history → potentially different TeachingAction.**

## 17. Observability

The system should expose:

-   Structured Agent outputs
-   Tool calls
-   Schema-validation results
-   State diffs
-   Latency
-   Token usage / cost
-   Model version
-   Prompt version
-   Deterministic test results
-   Grading benchmark results

## 18. TBD

The following implementation details require explicit definitions before
implementation:

- Mastery calculation
- Retention calculation
- Grader Rubric Standard
- Pass Threshold
- Review scheduling algorithm
- Conversation-context persistence
- HSK1 Teaching Materials Database coverage