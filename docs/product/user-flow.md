# MVP user flow

## First session

1. Learner creates an HSK1 goal and provides available study time.
2. Goal Planning Agent creates a short diagnostic plan.
3. Teaching Agent presents an open-ended exercise.
4. Grader returns structured rubric scores and immediate feedback.
5. Progress & Mastery updates learner state outside the critical response path.
6. Goal Planning creates or revises the daily plan when required.

## Returning session

1. The API restores learner state from SQLite.
2. The deterministic orchestrator checks goal change, due review, and plan validity.
3. The learner sees overall progress and today's plan.
4. Teaching continues the plan; due review and recurring errors influence content.
5. Session close persists a summary and seeds the next planning event.

## Failure and fallback behavior

- Invalid model output: reject it through Pydantic validation and retry within the configured limit.
- Hosted model unavailable or budget guard triggered: switch to the configured Ollama model.
- Retrieval unavailable: fall back to curated structured content.
- Background update fails: keep the accepted answer event for safe replay; do not silently lose progress.

`TODO(interface)`: define final HTTP error payloads, retry behavior, and learner-facing messages.
