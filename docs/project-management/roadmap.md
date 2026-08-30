# Four-week roadmap

The roadmap follows the senior review's capability milestones rather than dividing weeks into isolated technologies.

## Week 1 — It runs

Goal: deliver one primitive but complete HSK1 vertical learning loop.

- Finalize Pydantic contracts.
- Create SQLite schema, migrations, and repositories.
- Implement deterministic orchestration and initial retention calculation.
- Configure hosted/local OpenAI-compatible model clients.
- Seed enough licensed content for one concept flow.
- Persist a learner answer and updated state.

Exit criterion: `goal -> plan -> exercise -> answer -> grade -> progress update -> SQLite` works end to end.

## Week 2 — It adapts

Goal: make grading and learner history materially change the next plan.

- Implement structured grader and Teaching Agent.
- Implement mastery, retention, error, and review updates.
- Add remedial/review/new-content planning behavior.
- Expand curated HSK1 material.
- Create the human-labelled grading benchmark.
- Compare structured retrieval with semantic retrieval candidates.

Exit criterion: two contrasting learner states produce explainably different next plans.

## Week 3 — It works as an app

Goal: integrate the proven loop into a usable multi-session application.

- Connect FastAPI endpoints and dependency wiring.
- Run non-urgent state/planning work outside the synchronous response path.
- Connect the Streamlit plan, exercise, feedback, and progress views.
- Record latency, tokens, cost, model, prompt version, and fallbacks.
- Test close/reopen persistence and recovery behavior.

Exit criterion: a learner completes sessions through the UI and restored state influences the next visit.

## Week 4 — We can prove it

Goal: validate, harden, and demonstrate the product behavior.

- Measure grader agreement against human ground truth.
- Analyze rubric-level and Chinese-specific errors.
- Tune prompts and provisional thresholds with regression tests.
- Exercise hosted failure and local Ollama fallback.
- Test cost and latency limits.
- Freeze the demo dataset and walkthrough.

Exit criterion: evaluation results and a repeatable offline-capable demo prove the adaptive loop.

`TODO(schedule)`: add calendar dates after the sprint start date is confirmed.
