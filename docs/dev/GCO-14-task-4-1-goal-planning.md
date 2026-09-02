# Summary

This pull request delivers a **partial implementation of GCO-14 (Goal Planning)**. It adds the deterministic core that consumes the existing `LearningGoal` and `ConceptMastery` state and produces a validated `DailyPlan` containing ordered `PlanItem` entries.

This PR completes the goal-processing and daily-plan-generation portions of GCO-14. Curriculum prerequisite integration and learner repository integration remain follow-up work.

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

| Issue | Scope in this PR | Status |
|---|---|---|
| [GCO-14](https://psyche97.atlassian.net/browse/GCO-14) | Parent Goal Planning task | Partial / In Progress |
| [GCO-62](https://psyche97.atlassian.net/browse/GCO-62) | Process learning goal | Complete |
| [GCO-64](https://psyche97.atlassian.net/browse/GCO-64) | Generate learning plan | Complete |
| [GCO-63](https://psyche97.atlassian.net/browse/GCO-63) | Select learning concepts | Partially complete |
| [GCO-67](https://psyche97.atlassian.net/browse/GCO-67) | Read learner state | Planner-level consumption only |

## Not included / follow-up work

- Read concept metadata and prerequisite relationships from the curriculum repository.
- Enforce prerequisite-aware selection before marking GCO-63 complete.
- Load `LearnerState` through the learner repository and persist the generated plan in the application integration layer.
- Validate the `0.60` remedial threshold and five-minute default item duration with the team or empirical evaluation.
- Complete integration tests for the database-to-planner workflow.

## Reviewer checklist

- [x] Reuses the existing Pydantic domain contracts.
- [x] Preserves the existing `GoalPlanner` protocol.
- [x] Produces deterministic, time-bounded plans.
- [x] Adds focused unit tests.
- [x] Does not change teammate-owned ORM, persistence, retrieval, grading, or orchestration code.
- [x] Does not include secrets, generated databases, or personal learner data.
- [ ] Prerequisite-aware concept selection will be completed separately.
- [ ] Learner repository integration will be completed separately.

## Suggested PR title

```text
feat(planning): add deterministic daily plan generation
```

> This PR does not close GCO-14; it implements GCO-62 and GCO-64 and provides the deterministic foundation for the remaining integration work.


[GCO-14]: https://psyche97.atlassian.net/browse/GCO-14?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ