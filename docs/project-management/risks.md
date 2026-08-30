# Risk register

Probability and impact use `Low`, `Medium`, or `High` until the team adopts a numeric scale.

| Risk | Probability | Impact | Mitigation / trigger | Proposed owner | Status |
|---|---|---|---|---|---|
| Sequential LLM calls produce 15–25 second latency | High | High | Keep one synchronous loop; background deterministic updates; trace latency | Core/API | Open |
| Hosted model debugging exceeds $50/week | High | High | Budget guard, cheap Chinese-capable model, caching, usage telemetry | AI | Open |
| Grader mishandles Hanzi, pinyin, tones, particles, or word order | High | High | Gated rubric, human benchmark, confidence handling, regression suite | AI/Data | Open |
| One noisy grade distorts mastery | Medium | High | Multiple evidence points and bounded updates | Progress | Open |
| Unlicensed or mismatched HSK content enters repository | Medium | High | Source/license register and content review before ingestion | Data | Open |
| LangGraph/ChromaDB consume sprint without demonstrated need | Medium | High | Disabled by default; require benchmark/ADR before adoption | Lead | Open |
| Background update is lost or duplicated | Medium | High | Durable event/idempotency design and recovery integration test | Backend | Open |
| Hosted model fails during final demo | Medium | High | Pre-pulled Ollama model, offline rehearsal, fixed demo content | AI/Core | Open |
| Team interfaces diverge | Medium | High | Pydantic contracts first and contract examples/tests | Team lead | Open |
| Scope expands beyond HSK1 adaptive loop | High | Medium | Enforce MVP scope and weekly exit criteria | Team lead | Open |
| SQLite concurrency causes locking issues | Low | Medium | Short transactions, single-writer strategy, retry policy | Backend | Open |
| Learner answers leak through logs | Medium | High | Privacy policy, redaction, no raw answers by default | Backend/Lead | Open |

At each weekly review, update status and add evidence. Materialized risks should become backlog items.
