# GCO-62 and GCO-64 Goal Planning Core

## Summary

This document records the first implementation phase of **GCO-14 (Goal Planning)**. Its scope is GCO-62 and GCO-64: processing the existing learning goal and generating a deterministic daily plan.

Curriculum prerequisite checking, learner-state loading, and persistence were not part of this phase. Those later changes are documented in [`GCO-63-GCO-67-planning-integration.md`](GCO-63-GCO-67-planning-integration.md).

## What changed

- Added `DeterministicGoalPlanner` using the existing asynchronous `GoalPlanner` interface:

  ```python
  async def create_plan(self, state: LearnerState) -> DailyPlan
  ```

- Added deterministic plan-item prioritization:
  1. `REVIEW` - concepts whose scheduled review is due.
  2. `REMEDIAL` - studied concepts below the configured mastery threshold.
  3. `NEW` - concepts not present in learner mastery, ordered by the HSK1 sequence.
- Enforced `LearningGoal.daily_available_minutes` during plan allocation.
- Prevented due concepts from also being added as remedial items.
- Added a lowest-retention fallback when no normal candidate is available.
- Added a concise rationale to each generated plan.
- Added focused unit tests for the implemented behavior.

## Design decisions

- Planning remains deterministic because priority selection, mastery checks, ordering, and time allocation are rule-based operations.
- The planner does not call an LLM.
- The planner consumes `LearnerState` but does not load from or save to SQLite.
- The supplied learner state is not mutated.
- Existing domain models, retention calculations, enums, ORM models, persistence code, retrieval code, grading code, and orchestrator code were not changed.
- The clock and curriculum sequence are injectable, allowing deterministic tests and later configuration changes.

## Files changed

- `src/goalcoach/agents/goal_planning.py`
- `tests/unit/test_goal_planning.py`

## Tests

```bash
uv run pytest tests/unit/test_goal_planning.py -v
```

Result:

```text
5 passed in 0.37s
```

The tests verify:

- `REVIEW -> REMEDIAL -> NEW` ordering;
- new learners start from the first HSK1 concept;
- generated plans do not exceed the daily time budget;
- due and weak concepts are not duplicated;
- a missing `LearningGoal` produces a clear error.

## Jira scope

| Issue | Scope in this phase | Status |
|---|---|---|
| [GCO-14](https://psyche97.atlassian.net/browse/GCO-14) | Parent Goal Planning task | Partial / In Progress |
| [GCO-62](https://psyche97.atlassian.net/browse/GCO-62) | Process learning goal | Complete |
| [GCO-64](https://psyche97.atlassian.net/browse/GCO-64) | Generate learning plan | Complete |
| [GCO-63](https://psyche97.atlassian.net/browse/GCO-63) | Prerequisite-aware concept selection | Not included in this phase |
| [GCO-67](https://psyche97.atlassian.net/browse/GCO-67) | Read learner state | Not included in this phase |

## Follow-up work completed separately

The following work was completed after this initial planner phase and is documented separately:

- GCO-63 prerequisite-aware `NEW` concept selection;
- GCO-67 learner-state loading through `LearnerRepository`;
- assignment of the generated plan to `LearnerState.active_plan`;
- atomic persistence of the updated learner aggregate;
- configurable planning item duration;
- database-to-planner integration coverage.

See [`GCO-63-GCO-67-planning-integration.md`](GCO-63-GCO-67-planning-integration.md).

## Reviewer checklist

- [x] Reuses the existing Pydantic domain contracts.
- [x] Preserves the existing `GoalPlanner` protocol.
- [x] Produces deterministic, time-bounded plans.
- [x] Adds focused unit tests.
- [x] Does not change teammate-owned ORM, persistence, retrieval, grading, or orchestration code.
- [x] Does not include secrets, generated databases, or personal learner data.
- [x] This phase remains limited to GCO-62 and GCO-64.
- [x] Follow-up prerequisite and persistence work is documented separately.

## Suggested PR title

```text
feat(planning): add deterministic daily plan generation
```

> This phase implements GCO-62 and GCO-64. Later GCO-63 and GCO-67 integration work is intentionally recorded in a separate development document so that the scope of this original planner implementation remains clear.


[GCO-14]: https://psyche97.atlassian.net/browse/GCO-14?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
