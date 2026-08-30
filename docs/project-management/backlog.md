# MVP backlog

Status values: `TODO`, `IN PROGRESS`, `BLOCKED`, `DONE`. Owners below are proposed from the proposal roles and must be confirmed.

| Priority | Capability | Work item | Proposed owner | Status | Acceptance evidence |
|---|---|---|---|---|---|
| P0 | Core | Confirm domain schemas and interface contracts | Weijia + team | TODO | Team-reviewed schemas and examples |
| P0 | Persistence | Implement SQLite schema, migrations, and repositories | Jiyan | TODO | Repository integration tests pass |
| P0 | Workflow | Complete deterministic routing and learning-loop service | Musab / Weijia | TODO | Branch and end-to-end tests pass |
| P0 | Grading | Implement schema-constrained six-dimension grader | Weijia / Weng Man | TODO | Valid structured outputs on benchmark |
| P0 | Progress | Implement mastery, retention, error, and review updates | Musab / Weijia | TODO | Deterministic unit tests pass |
| P0 | Content | Confirm HSK version, sources, licenses, and concept taxonomy | Weng Man | TODO | Reviewed source register and sample dataset |
| P0 | Planning | Implement diagnostic and adaptive daily planning | Weijia | TODO | Contrasting learner-state scenario passes |
| P1 | Teaching | Implement exercise, explanation, and feedback behavior | Weng Man / Weijia | TODO | Reviewed HSK1 interaction samples |
| P1 | API | Implement goal, plan, exercise, answer, progress, and session endpoints | Jiyan | TODO | API integration tests pass |
| P1 | Async | Decouple non-urgent updates from response path | Jiyan / Musab | TODO | Latency trace shows no sequential agent chain |
| P1 | Evaluation | Label and adjudicate 30–50 representative HSK1 answers | Weng Man + team | TODO | Versioned benchmark and annotation guide |
| P1 | Models | Add hosted client, budget guard, and Ollama fallback | Musab / Weijia | TODO | Forced-fallback test passes |
| P1 | UI | Connect daily plan, exercise, feedback, and progress dashboard | `TODO(owner)` | TODO | Complete learner flow through Streamlit |
| P1 | Telemetry | Record latency, tokens, cost, validation, and fallback | Musab / Jiyan | TODO | Trace attached to a complete session |
| P2 | Retrieval | Benchmark SQL/metadata versus vector retrieval | Weng Man / Weijia | TODO | Recorded comparison and ADR |
| P2 | Workflow | Evaluate LangGraph against plain Python implementation | Musab / Weijia | TODO | ADR documents measured benefit or rejection |
| P2 | Demo | Seed two contrasting learners and scripted review decay | Team | TODO | Repeatable demo rehearsal passes |

`TODO(team)`: confirm Musab's current team membership and every proposed ownership assignment.
