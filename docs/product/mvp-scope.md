# MVP scope

## Product objective

Prove that persistent learner state can adapt an HSK1 learning plan across sessions:

```text
Goal -> Plan -> Teach -> Grade -> Update -> Adapt -> Re-plan
```

## Included

- One HSK1 goal and a short diagnostic starting point.
- Curated, licensed HSK1 concepts and open-ended exercises.
- Daily plan containing review, remediation, and new learning.
- Structured Chinese grading across six rubric dimensions.
- Concept mastery, retention, recurring error profile, and review schedule.
- Honest progress computed from mastery multiplied by retention.
- Multi-session SQLite persistence.
- Minimal FastAPI API and Streamlit learner experience.
- Human-labelled grader benchmark and error analysis.
- Hosted model with a local Ollama demonstration fallback.

## Excluded from the four-week MVP

- Full HSK1–6 content coverage.
- Production authentication, billing, social features, or gamification.
- Native mobile applications.
- Mandatory LangGraph or ChromaDB adoption.
- A second LLM judge on every runtime answer.
- Production-scale deployment and analytics.

## Success evidence

1. Two learners with the same goal but different histories receive different plans.
2. A target-concept error changes mastery, error profile, and subsequent remediation.
3. Retention decay causes a previously learned concept to re-enter review.
4. State survives application restart and affects the next session.
5. The grader produces schema-valid results and is measured against human labels.
6. The demo remains operable through the configured local fallback.

`TODO(product)`: confirm HSK version, content sources, target persona details, and measurable grader acceptance threshold.
