# GoalCoach

GoalCoach is an adaptive AI learning coach for Chinese-as-a-second-language learners. The MVP focuses on HSK1 and proves one complete learning loop:

```text
Goal -> Plan -> Teach -> Grade -> Update learner state -> Adapt -> Re-plan
```

Unlike a fixed course or a stateless chatbot, GoalCoach persists concept-level mastery, estimated retention, recurring errors, review dates, and session history. It uses that state to decide what a learner should study next and computes progress from both mastery and retention.

> Status: early project scaffold derived from the documents in [`Proposal/`](Proposal/). The 30-year Senior AI Engineering Review is the primary engineering blueprint; the supplementary document clarifies its ambiguous points. Interfaces are defined first, and unconfirmed decisions are marked `TODO(decision)`.

## MVP scope

- One learning target: HSK1 (the architecture remains level-agnostic).
- Open-ended Chinese exercises with rubric-based structured grading.
- Deterministic workflow routing and state updates where rules are sufficient.
- LLM use only for language-heavy work: grading, feedback, explanations, and optionally complex planning.
- Persistent learner state in SQLite.
- FastAPI backend and a minimal Streamlit client.
- Human-labelled grader benchmark before introducing a second judge model.
- Structured content lookup first; vector retrieval only after its value is measured.

Not in the initial MVP: broad HSK1–6 content coverage, production authentication, social/gamification features, or mandatory LangGraph/ChromaDB infrastructure.

## Architecture

```text
Streamlit / future web client
            |
         FastAPI
            |
    Application services
            |
  Deterministic orchestrator
    |       |       |       |
 planner  teacher  grader  progress
    |       |       |       |
    +-------+-------+-------+
            |
     Repository interfaces
       |             |
     SQLite       content lookup
                       |
              optional vector search

Hosted LLM or local Ollama is accessed through one provider-neutral interface.
```

The learner-facing answer path should remain short: `answer -> grader -> immediate teaching feedback`. Deterministic progress persistence and non-urgent re-planning can happen outside that critical response path.

### Senior-review constraints

The implementation must preserve these constraints from the architecture verdict:

- Never execute Planner, Progress, Retrieval, Grader, and Teacher as a sequential LLM chain for one answer.
- Keep one synchronous interaction loop; move deterministic state recalculation and non-urgent planning to background work.
- Validate every model response with Pydantic v2 schemas.
- Persist learner truth in SQLite; run ChromaDB embedded only if semantic retrieval proves useful.
- Access hosted and local models through the same OpenAI-compatible interface, switching by configuration.
- Prefer Chinese-capable, cost-efficient models and record token, cost, latency, model, and prompt version.
- Maintain a fully local Ollama fallback for the final demonstration.
- Treat grading reliability as a deliverable, using human-labelled answers and rubric-level agreement metrics.

See the [proposal traceability matrix](docs/architecture/proposal-traceability.md) for how each verdict maps to the repository.

### Routing priority

1. Goal created or changed: create/rebuild the roadmap.
2. Review due: incorporate review work into the active plan.
3. Plan missing, invalid, or exhausted: regenerate the daily plan.
4. Otherwise: continue today's teaching plan.

Progress and planning are separate concerns: progress describes the learner's current state; planning consumes that state and selects what happens next.

## Repository layout

```text
apps/
  api/                 FastAPI composition root and HTTP routes
  web/                 Streamlit MVP client
src/goalcoach/
  domain/              Stable Pydantic models and enums
  application/         Use cases and workflow orchestration
  agents/
    goal_planning.py   Goal Planning Agent
    progress_mastery.py Progress & Mastery Agent
    retrieval.py       Retrieval Agent
    teaching.py        Teaching Agent
    grading.py         Chinese Grader component
    interfaces.py      Shared Agent contracts
  infrastructure/      SQLite, LLM, and retrieval adapters
tests/
  unit/                Domain and deterministic algorithm tests
  integration/         Persistence/API learning-loop tests
data/
  curriculum/          Licensed, curated HSK content
  evaluation/          Human-labelled grading benchmark
docs/
  architecture/        Design and interface documentation
  decisions/           Architecture decision records (ADRs)
  product/             MVP scope and user journey
  project-management/  Roadmap, backlog, risks, ownership, and demo readiness
scripts/               Data ingestion and evaluation utilities
Proposal/              Source proposal and review documents
```

## Core state and interfaces

The initial contracts live in [`src/goalcoach/domain/models.py`](src/goalcoach/domain/models.py):

- `LearnerState`: goal, plan, per-concept state, errors, and session history.
- `ConceptMastery`: mastery, retention, evidence count, and next review date.
- `DailyPlan`: ordered review/remedial/new-learning items.
- `Exercise` and `AnswerSubmission`: teaching interaction.
- `GradingResult`: explicit rubric dimensions and gating result.
- `ProgressUpdate`: deterministic state changes after grading.
- `RetrievalRequest`: exact/structured/semantic content request.

Protocols in [`src/goalcoach/agents/interfaces.py`](src/goalcoach/agents/interfaces.py) allow each team member to build an adapter without coupling the core to a particular model, database, or framework.

The Workflow Orchestrator is located in [`src/goalcoach/application/orchestrator.py`](src/goalcoach/application/orchestrator.py), not under `agents/`, because the proposal explicitly defines it as a deterministic controller rather than an LLM reasoning agent.

## Progress and grading

Headline progress is concept-weighted:

```text
progress = sum(concept_weight * mastery * current_retention)
           / sum(concept_weight)
```

Retention decays with elapsed time and is strengthened or reset after review. Exact decay parameters are intentionally configurable and need empirical validation.

Grading records semantic/task achievement, grammatical correctness, target-concept mastery, word order, completeness, and vocabulary appropriateness. Target-concept mastery and task achievement are gates; dimensions must not be blindly averaged. Mastery requires evidence across multiple exercises.

## Getting started

Prerequisites: Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
sqlite3 data/database1/goalcoach_hsk1_learning.db \
  < data/database1/GoalCoach_HSK1_Learning_DB_Package/data/goalcoach_hsk1_learning_db_sqlite.sql
pytest
uvicorn apps.api.main:app --reload
```

In another terminal, the placeholder client can be started with:

```bash
streamlit run apps/web/app.py
```

Database #1 structured content is available through the SQLAlchemy `ContentRepository`, with
typed mappings for concepts, teaching cards, exercises, prerequisites, and JSON fields. The API
still exposes health and interface-level placeholder endpoints: learner-state persistence and the
complete learning loop are not wired yet, so those endpoints intentionally return `501`.
Background-work interfaces are separated from the synchronous answer path so integration cannot
accidentally create the latency-heavy sequential agent chain warned about in the review.

## Configuration

See [`.env.example`](.env.example). `GOALCOACH_CONTENT_DATABASE_URL` configures Database #1;
its default is `sqlite:///./data/database1/goalcoach_hsk1_learning.db`. The separate
`GOALCOACH_DATABASE_URL` is reserved for learner-state persistence. The LLM interface is
OpenAI-compatible so a hosted gateway and local Ollama can share the same adapter.

The senior verdict recommends OpenRouter for hosted model experimentation and Ollama with Gemma/Qwen as the local fallback. The supplementary review asks the team to confirm OpenRouter versus Bedrock with the mentor, so this remains `TODO(decision)` rather than being silently fixed. Regardless of provider, adapters must remain OpenAI-compatible and configuration-driven.

## Four-week delivery plan

1. **It runs:** complete one primitive HSK1 vertical slice and persist learner state.
2. **It adapts:** validated grading updates mastery/errors and produces different plans for different learner states.
3. **It works as an app:** connect core, SQLite, API, and UI; verify state across sessions.
4. **We can prove it:** benchmark against human labels, tune thresholds, harden fallbacks, and prepare the demo.

The strongest demo is behavioral: two learners with the same HSK1 goal but different errors/retention receive different plans; a remembered error changes remediation, and retention decay later schedules review.

## Open decisions and required inputs

These are tracked in [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md). The most important inputs from the team are:

- hosted LLM/provider and local fallback;
- final planning frequency;
- validated rubric gates, mastery thresholds, and retention parameters;
- authoritative HSK version and content sources with redistribution rights;
- frontend choice after the Streamlit prototype;
- whether LangGraph and ChromaDB add measurable value.

Delivery planning is maintained in [`docs/project-management/`](docs/project-management/README.md). Original PDFs in `Proposal/` are treated as read-only source material; evolving decisions belong in docs or ADRs.

## Development principles

- Keep domain logic independent of FastAPI, Streamlit, model SDKs, and databases.
- Prefer deterministic code for routing, retention, aggregation, and exact lookup.
- Validate every LLM output against a strict schema.
- Never place secrets, learner data, or unlicensed source content in Git.
- Add a regression case whenever a grader prompt, rubric, or model changes.

## Team

- Weijia Han — AI / Agent Engineer, team lead
- Jiyan Wang — Backend Engineer
- Weng Man Cheung — AI / Data Engineer
- Musab — AI Engineer / Core Systems Architect

## License

`TODO(decision)`: choose a code license and document content/data licensing separately.
