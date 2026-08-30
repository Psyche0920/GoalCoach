# Architecture notes

## Critical path

The synchronous learner path should contain only work needed for useful immediate feedback: load exercise/state, grade the answer, and generate or select feedback. Progress persistence and plan regeneration should not add extra sequential LLM calls.

## Retrieval policy

- Known `concept_id`: relational exact lookup.
- Known metadata constraints: relational query/filter.
- Ambiguous error or semantic learning need: optional metadata-filtered vector retrieval.
- Reuse already-selected material when it still covers the gap.

## Framework policy

The architecture is a state machine. Begin with plain Python. Introduce LangGraph only if graph persistence, debugging, branching complexity, or observability provides concrete value. Keep domain and agent contracts framework-independent.

## Persistence boundary

SQLite owns users, goals, concept state, retention, errors, review dates, plans, exercises, and sessions. A later vector store owns embeddings and retrieval metadata, not learner truth.
