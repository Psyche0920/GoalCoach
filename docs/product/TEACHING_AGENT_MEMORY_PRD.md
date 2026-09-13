# Teaching Agent Memory PRD

**Product:** GoalCoach  
**Module:** Teaching Agent Memory  
**Status:** Draft for team review  
**Scope:** Current CLI Teaching Agent MVP and long-term memory architecture

---

## 1. Purpose

This document defines how GoalCoach remembers a learner across teaching turns, sessions, and application restarts. It separates conversational context from durable learning evidence so that pedagogical decisions remain explainable, testable, and cost-controlled.

The target learning loop is:

```text
Teach -> Answer -> Grade -> Record Attempt -> Update Learner State -> Adapt
```

Memory must support two different questions:

1. **Conversation continuity:** What has just happened in the current teaching interaction?
2. **Learning continuity:** What has the learner demonstrated over time, and how should future teaching change?

These concerns must not share one unbounded message log as their source of truth.

---

## 2. Product Principles

1. **Application-owned learning memory:** Learner progress is calculated and persisted by deterministic application services, not assigned by an LLM.
2. **Evidence before inference:** Mastery and error state must be derived from graded attempts.
3. **Short prompts, durable facts:** The database may retain extensive evidence, while each model call receives only the context required for the next teaching decision.
4. **Structured state over raw conversation:** Typed teaching turns, attempts, and learner state are preferred to replaying unlimited chat history.
5. **Separation of concerns:** Curriculum knowledge, learner data, and agent execution traces remain separate.
6. **Minimal MVP:** Message-history persistence and generated session summaries are deferred until they solve a demonstrated product need.
7. **Privacy and auditability:** Secrets and hidden model reasoning are never stored as learner memory.

---

## 3. Terminology

| Term | Meaning | Lifetime | Source of mastery evidence |
| --- | --- | --- | --- |
| PydanticAI Message History | Model requests, responses, tool calls, and tool results | One active conversation by default | No |
| Teaching Session | One bounded teaching interaction for a target concept | Current session; optionally durable later | No |
| Teaching Turn | One action selected by the Teaching Agent | Current session; optionally durable later | Only when it produces a graded attempt |
| Attempt | Exercise, learner answer, and grading result | Durable | Yes |
| Learner State | Current aggregate of mastery, progress, errors, and review schedule | Durable | Yes, derived from attempts |
| Session Summary | Optional compression of multiple turns | Deferred | No; advisory context only |
| Curriculum Memory | Concepts, cards, exercises, and prerequisites | Durable content knowledge | No |

---

## 4. Current Implementation

### 4.1 Current short-term memory

The current CLI Teaching Agent stores interaction history in an in-memory `TeachingSession`:

```text
TeachingSession
├── concept_id
├── status
└── turns[]
    ├── TeachingAction
    ├── learner_response (optional)
    └── GradingResult (optional)
```

All turns produced during the current process are appended to `TeachingSession.turns`. Before each Teaching Agent decision, only the most recent three turns are converted to text and included in the next prompt:

```python
recent_turns = session.turns[-3:]
```

Consequences:

- The Agent can react to the latest teaching actions, answers, and grades.
- The in-memory session retains all turns during the current run.
- The model only sees the latest three turns.
- When the program exits, the session and turns disappear.

### 4.2 Current learner context

The runner constructs a new test `LearnerState` on every startup. The Teaching Agent currently reads:

- target HSK level;
- up to three recent error codes, if present.

The current teaching loop does not:

- load an existing learner from the learner repository;
- update mastery or concept progress;
- update the error profile;
- persist the learner state;
- restore state on the next process start.

Therefore, the current `LearnerState` is static dependency context, not operational long-term memory.

### 4.3 Current PydanticAI message history

PydanticAI internally retains messages during a single `agent.run()` call. They are available through results such as:

```python
result.all_messages()
result.new_messages()
```

The current Teaching Agent returns only the structured output and provider. It does not retain or pass `message_history` into the next `agent.run()` call.

Current status:

```text
Message memory inside one agent.run():       available
Message history across agent.run() calls:    not used
Persisted message history:                   not implemented
Recent cross-turn context:                   supplied through TeachingSession
```

### 4.4 Current durable event infrastructure

The learner database infrastructure already defines:

- `learner_states`: current learner aggregate snapshots;
- `learning_events`: immutable study and grading event records;
- repository methods to save learner state and record learning events.

However, the Teaching Agent loop does not yet call these repository methods.

The existing `LearningEvent` is generic and currently lacks explicit fields for:

- the learner's submitted answer;
- a complete generated exercise snapshot;
- Teaching Session and Teaching Turn identifiers;
- the Teaching Agent action associated with the attempt.

It is therefore not yet a complete Teaching Agent Attempt record.

---

## 5. Database Boundaries

### 5.1 Curriculum database

```text
data/database1/goalcoach_hsk1_learning.db
```

Responsibilities:

- curriculum concepts;
- teaching cards;
- fixed exercises;
- prerequisites.

This database answers: **What can the system teach?**

### 5.2 Learner database

```text
goalcoach.db
```

Current intended responsibilities:

- learner-state snapshots;
- mastery and concept progress;
- recurring error profile;
- review schedule;
- learning and attempt events.

This database answers: **What has this learner demonstrated, and what should change?**

Curriculum content must not be duplicated into learner state unless a generated exercise needs an immutable snapshot for auditability.

---

## 6. MVP Memory Requirements

### 6.1 MVP scope

The MVP will use three memory components only:

```text
1. TeachingSession in memory
2. Durable graded Attempts
3. Durable LearnerState
```

The MVP will not require:

- persisted raw PydanticAI message history;
- an LLM-generated Session Summary;
- Redis;
- vector storage of learner history;
- LangGraph;
- storage of model reasoning.

### 6.2 Teaching Session requirements

During an active process, the system must:

- retain all Teaching Turns in the active `TeachingSession`;
- provide only a bounded recent-turn context to the Teaching Agent;
- keep the target concept and completion status explicit;
- terminate using deterministic completion and safety rules.

A Teaching Turn is not automatically an Attempt:

```text
explain                 -> Teaching Turn only
hint                    -> Teaching Turn only
remediate without input -> Teaching Turn only
ask + answer + grade    -> Teaching Turn and Attempt
```

### 6.3 Attempt persistence requirements

When a Teaching Turn contains both a learner response and a grading result, the system must create an immutable Attempt event.

Minimum Attempt information:

```text
Identity
├── event_id
├── learner_id
├── session_id
├── turn_id
└── concept_id

Exercise
├── exercise_id
├── prompt
├── target_instruction
├── exercise_type
├── reference_answers
└── source/content_version when available

Submission
├── answer
└── submitted_at

Grading
├── scores
├── passed_gates
├── detected_errors
├── feedback
├── confidence
├── evidence
└── grader_version

Execution metadata
├── teaching_action_type
├── model/provider when applicable
└── created_at
```

For a fixed curriculum exercise, `exercise_id` and content version provide the canonical reference. For an Agent-generated exercise, the complete exercise snapshot must be stored because the generated identifier alone cannot reconstruct the original task.

### 6.4 Learner-state update requirements

After a graded Attempt:

1. Persist the immutable Attempt.
2. Pass its structured evidence to the deterministic progress reducer.
3. Update relevant concept progress, mastery, retention, and error profile.
4. Persist the updated `LearnerState` snapshot.
5. Supply the new relevant state to the next Teaching Agent decision.

The Teaching Agent may decide **how to teach next**, but it must not directly assign mastery scores or mutate authoritative learner state.

### 6.5 Transaction and failure requirements

- Duplicate events must not apply progress twice.
- Failed persistence must not silently report a successful state update.
- An invalid or incomplete grading result must not affect mastery.
- Attempt evidence must remain recoverable even if a later model call fails.
- Repository failures must surface as explicit domain/infrastructure errors.

---

## 7. MVP Data Flow

```text
Teaching Agent selects TeachingAction
                 |
                 v
           User responds
                 |
                 v
          Grader evaluates
                 |
                 v
    Append TeachingTurn to active session
                 |
                 v
       Create immutable Attempt Event
                 |
                 v
        Save to learning_events
                 |
                 v
    Deterministic Progress Reducer
                 |
                 v
 Update mastery / progress / error profile
                 |
                 v
       Save LearnerState snapshot
                 |
                 v
 Agent reads bounded recent turns + new state
```

---

## 8. PydanticAI Message-History Policy

### 8.1 MVP decision

The MVP will not pass complete PydanticAI message history between Teaching Agent runs. `TeachingSession` remains the application-owned source of short-term pedagogical context.

Rationale:

- current interactions are structured exercise cycles, not open-ended chat;
- recent Teaching Turns already provide the required observations;
- using both full message history and recent-turn text would duplicate context;
- unlimited tool results and messages increase latency, cost, and prompt ambiguity;
- the model must not become the source of truth for learner progress.

PydanticAI continues to manage the internal model/tool loop within each individual `agent.run()` call.

### 8.2 When message history becomes necessary

Introduce bounded PydanticAI message history when the product supports natural follow-up dialogue such as:

```text
"Why can't I use 会 here?"
"What did you mean by the previous example?"
"Explain that again in a simpler way."
```

At that point, message history should complement, not replace, Teaching Turns and Learner State.

### 8.3 Context-budget policy

When enabled, the Agent context should contain:

```text
Current teaching objective
+ relevant concept-specific LearnerState
+ latest 3-5 complete turns/messages
+ optional compact older-history summary
```

It must not contain the learner's complete lifetime conversation. The usable model context is shared by instructions, tool schemas, retrieved curriculum, message history, and output tokens.

---

## 9. Session Summary Decision

### 9.1 MVP decision

A generated Session Summary is deferred. For the current short concept-level loop, maintaining Attempts, LearnerState, Teaching Turns in memory, and a minimal completion record is sufficient.

The existing `SessionSummary` domain model may remain unused until a concrete product requirement appears.

### 9.2 Minimal session completion record

If session-level reporting is needed during the MVP, store only deterministic metadata:

```text
session_id
learner_id
concept_id
status
completion_reason
attempt_count
passed_count
started_at
ended_at
```

No LLM-generated narrative is required.

### 9.3 Long-term trigger for summaries

Add Session Summaries only when at least one condition is true:

- sessions contain many turns;
- free-form dialogue is supported;
- users can resume a previous session;
- prior teaching-strategy effectiveness must influence future sessions;
- context size becomes materially costly;
- the product displays a learner-facing session recap.

When introduced, a Session Summary is a compression of multiple turns, not a replacement for Attempts. It should reference Attempt IDs rather than duplicate every question and answer.

---

## 10. Long-Term Memory Architecture

### 10.1 Target storage model

```text
goalcoach.db
├── learner_states
│   └── Current mastery, progress, errors, and review schedule
├── learning_events / attempts
│   └── Immutable exercises, submissions, and grades
├── teaching_sessions
│   └── Session identity, lifecycle, outcome, and optional summary
├── teaching_turns
│   └── Ordered pedagogical actions selected by the Agent
├── agent_runs
│   └── Model, provider, tools, usage, latency, and failures
└── agent_message_histories (optional)
    └── Temporarily retained raw messages for resumable conversations
```

### 10.2 Teaching Turn persistence

Persist Teaching Turns when the product needs to audit or analyze how the Agent taught, including non-graded actions.

Recommended fields:

```text
turn_id
session_id
sequence_number
action_type
content
objective
expected_response
exercise_id (optional)
retrieved_card_ids
created_at
```

Teaching Turns answer: **What did the Agent do?**

Attempts answer: **What did the learner demonstrate?**

### 10.3 Optional Agent-run metadata

For observability and evaluation, retain compact execution metadata:

```text
run_id
turn_id
agent_name
model
provider
prompt_version
tool_names
retrieved concept/card identifiers
input_tokens
output_tokens
latency_ms
success/error category
created_at
```

Repeated curriculum content and raw tool payloads should normally be referenced by ID rather than copied.

### 10.4 Optional raw message persistence

Raw PydanticAI message history may be persisted only when needed for:

- resuming unfinished conversations;
- reproducing Agent failures;
- evaluating prompt and tool behavior;
- diagnosing repeated or inappropriate teaching actions.

Recommended policy:

| Data | Retention |
| --- | --- |
| Attempts | Long-term |
| LearnerState | Long-term current snapshot |
| Teaching Turns | Long-term when audit/analytics is needed |
| Minimal Session records | Long-term |
| Session Summaries | Long-term when enabled |
| Agent-run metadata | 30-90 days or aggregated longer |
| Raw message history | Active session or 7-30 days |
| Hidden model reasoning | Never |

For the local MVP, SQLite is sufficient. Redis may later hold active multi-user sessions with a TTL, but it is not required for the current milestone.

---

## 11. Capacity and Retrieval Strategy

The learner database may retain large numbers of events; the Agent must retrieve only a small relevant subset.

Recommended retrieval keys:

```text
learner_id
concept_id
session_id
created_at
event_type
```

The next Teaching Agent call should receive:

- current target concept;
- current concept progress and mastery;
- relevant recurring errors;
- recent 3-5 turns;
- selected recent failed Attempts when necessary;
- optional recent Session Summary when the feature exists.

Structured learner events should be queried through SQLite/PostgreSQL, not embedded into ChromaDB. ChromaDB remains a curriculum-material retrieval service.

---

## 12. Privacy and Security

The memory system must never persist:

- API keys or authentication headers;
- hidden chain-of-thought or internal model reasoning;
- redundant complete system prompts on every event;
- unnecessary sensitive learner data;
- unlimited raw tool results;
- duplicate copies of curriculum content without a versioning need.

Learner answers may contain personal information. Future production work must define consent, retention, deletion, export, and access-control policies before multi-user deployment.

---

## 13. Phased Delivery

### Phase 0 - Current state

- TeachingSession exists in memory.
- All current turns are appended during the process.
- Only the latest three turns are supplied to the Agent.
- LearnerState is created fresh by the CLI runner.
- Message history, Attempts, and learner changes are not persisted by the Teaching loop.

### Phase 1 - MVP long-term learning memory

- Run the Teaching Agent successfully end to end.
- Convert graded Teaching Turns into durable Attempt events.
- Persist complete generated-exercise snapshots, answers, and grades.
- Apply the deterministic progress reducer.
- Persist and reload LearnerState.
- Verify that a previous-session error changes a later teaching decision.

### Phase 2 - Durable teaching sessions

- Add stable session and turn identifiers.
- Persist minimal session completion records.
- Persist Teaching Turns if audit or teaching-strategy analytics requires them.
- Add total-turn safety limits independent of graded-attempt limits.

### Phase 3 - Conversational continuity

- Add bounded PydanticAI message history for free-form follow-up dialogue.
- Support active-session resume.
- Add token-budget trimming and optional rolling summaries.
- Add a retention policy for raw histories.

### Phase 4 - Observability and evaluation

- Record prompt/model/grader versions.
- Record provider, tool identifiers, token usage, latency, and errors.
- Evaluate teaching-policy quality and repeated-action behavior.
- Add session summaries only if supported by product evidence.

---

## 14. MVP Acceptance Criteria

The memory MVP is complete when:

1. A learner completes at least one graded Teaching Agent Attempt.
2. The exercise snapshot, learner answer, and complete grading result are persisted.
3. The Attempt is linked to the learner and target concept.
4. The Attempt updates mastery, concept progress, or error profile through deterministic rules.
5. The updated LearnerState is saved to `goalcoach.db`.
6. After restarting the program, the same learner state is loaded.
7. The next Teaching Agent decision receives the relevant updated state.
8. Duplicate Attempt processing does not update progress twice.
9. No raw message-history persistence is required to pass the MVP.
10. No secret or hidden model reasoning is stored.

---

## 15. Explicit Non-Goals for the Current MVP

- Unlimited conversational memory.
- Lifetime replay of every model message.
- LLM-generated mastery scores.
- LLM-generated Session Summaries.
- Redis or distributed session storage.
- Semantic search over learner history.
- Multi-agent shared memory.
- Production analytics warehouse.
- LangGraph-based memory orchestration.

---

## 16. Final Product Decision

For the current Teaching Agent MVP:

```text
Short-term teaching memory  = TeachingSession + latest three turns
Durable learning evidence   = graded Attempts
Durable learning state      = LearnerState
PydanticAI message history  = not persisted and not passed across runs
Session Summary             = deferred
```

This is the smallest architecture that proves GoalCoach can learn from a user's prior performance across application restarts without turning the product into an unbounded chatbot-memory system.
