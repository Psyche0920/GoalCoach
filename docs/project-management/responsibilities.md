# Responsibilities

These ownership boundaries are proposed from the roles stated in the proposal. They require team confirmation and do not prevent collaborative review.

| Area | Proposed accountable owner | Supporting members |
|---|---|---|
| Product scope, agent behavior, planning, coordination | Weijia Han | Entire team |
| FastAPI, SQLite, repositories, integration | Jiyan Wang | Musab |
| Curriculum, linguistic quality, error taxonomy, evaluation data | Weng Man Cheung | Weijia |
| Core orchestration, model adapters, fallback, telemetry | Musab | Weijia, Jiyan |
| Grading rubric and prompt validation | Weijia + Weng Man | Musab |
| Frontend / Streamlit | `TODO(owner)` | Backend and product owners |
| Evaluation adjudication | `TODO(owner)` | At least two human annotators |
| Demo narrative and rehearsal | Weijia | Entire team |

## Required cross-review

- Domain schema changes: core, backend, and data review.
- Grading/rubric changes: linguistic and AI review plus benchmark run.
- Persistence changes: backend review plus migration/integration tests.
- Scope or architecture changes: team decision recorded as an ADR.

`TODO(team)`: confirm whether Musab is a current member and replace every placeholder with a named accountable owner.
