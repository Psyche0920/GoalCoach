# Proposal traceability

This matrix makes the Senior AI Engineering Review actionable. “Planned” means the interface or directory exists but implementation is intentionally left marked rather than fabricated.

| Senior-review verdict | Project response | Status / location |
|---|---|---|
| Deterministic top-level routing | Plain Python priority router | Implemented in `ui/orchestrator.py` |
| Explicit specialized components | Named Goal Planning, Progress & Mastery, Retrieval, Teaching, and Grader modules | Scaffolded in `agents/` |
| Avoid sequential agent/LLM latency | Short answer path plus background state-update boundary | Contract in `ui/interfaces.py`; integration TODO |
| Interfaces first | Strict Pydantic domain contracts and Protocols | Implemented in `domain/models.py` and `agents/interfaces.py` |
| FastAPI + Pydantic v2 | API composition root and strict dependency versions | Scaffolded in `apps/api` and `pyproject.toml` |
| SQLite for durable learner state | Dedicated persistence adapter boundary | Content repository implemented with SQLAlchemy; learner-state repository planned |
| Embedded ChromaDB | Optional dependency behind retrieval boundary | Disabled by default; benchmark required |
| OpenRouter hosted models | OpenAI-compatible configurable endpoint | Configuration ready; provider/model decision open |
| Ollama Gemma/Qwen backup | Configurable local OpenAI-compatible endpoint | Default fallback URL defined; model decision open |
| $50/week budget risk | Weekly budget configuration plus required cost telemetry | Interface/config ready; enforcement TODO |
| Chinese grading risk | Six-dimensional gated rubric, confidence and prompt/grader version | Schema implemented; prompt and benchmark TODO |
| 20–30/25 human examples in review | Supplementary clarification raises MVP target to 30–50 HSK1 answers | Dataset directory defined; labels TODO |
| ChromaDB with curated resources | Structured curriculum directory; vector retrieval only if valuable | Data/retrieval scaffolds exist; licensed content TODO |
| Week 1 state and persistence | Vertical-loop tests and SQLite adapter | Content repository and integration tests implemented; learner-state repository/loop TODO |
| Week 2 grader and teaching loop | Grader/Teacher contracts and evaluation directory | Interfaces exist; implementation TODO |
| Week 3 API and async persistence | FastAPI boundary and background updater | API scaffold exists; wiring TODO |
| Week 4 UI, fallback, validation, demo | Streamlit shell, fallback config, benchmark and demo-seed script plan | Scaffolded/planned |

## Clarification precedence

Where the original proposal/review and supplementary feedback differ, the scaffold uses the later clarification:

- HSK1 is the MVP proving ground, while the architecture remains extensible to higher levels.
- Goal Planning runs both for long-term goal changes and short-term plan regeneration.
- Progress updates happen after exercises; major planning should normally occur at session boundaries or plan-invalidating events.
- State machine is the architecture; LangGraph is only one possible implementation.
- SQL/metadata lookup precedes vector retrieval for a small corpus.
- Human labels are the grading benchmark; a second LLM judge is optional.

Any change to these interpretations should be recorded as an ADR.
