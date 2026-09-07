# GCO-63 and GCO-67 Planning Integration

## Summary

This document records the second implementation phase of **GCO-14 (Goal Planning)**. Its scope is GCO-63 and GCO-67: selecting prerequisite-safe learning concepts and reading the current learner state through the repository boundary.

This phase also completes the orchestrator handoff requested during review. The generated `DailyPlan` is assigned to a copied `LearnerState.active_plan` and atomically persisted without mutating the state supplied to the planner.

The initial goal-processing and deterministic-plan-generation work is documented in [`GCO-62-GCO-64-goal-planning-core.md`](GCO-62-GCO-64-goal-planning-core.md).

## What changed

- Added prerequisite-aware selection for `NEW` concepts:
  - loads all 18 prerequisite relationships from `goalcoach_hsk1_learning.db`;
  - requires every prerequisite to exist in `state.mastery`;
  - requires mastery evidence before a prerequisite is accepted;
  - requires prerequisite mastery to meet the configured threshold;
  - rejects unknown concepts and self-dependencies during planner construction.
- Preserved deterministic plan-item prioritization:
  1. `REVIEW` - concepts whose scheduled review is due.
  2. `REMEDIAL` - studied concepts below the remedial threshold.
  3. `NEW` - unseen concepts whose prerequisites are satisfied.
- Added `SqlAlchemyLearnerRepository` for validated learner-state reads and atomic snapshot persistence.
- Added `PlanningOrchestrator` to perform:

  ```text
  Load LearnerState -> Create DailyPlan -> Copy state -> Assign active_plan -> Save state
  ```

- Added FastAPI dependency assembly and endpoints for reading learner state and generating plans.
- Made the planning item duration configurable through `GOALCOACH_PLANNING_ITEM_MINUTES`.
- Added unit and integration tests for prerequisites, configuration, orchestration, and persistence.
- Removed temporary Chinese learning comments after the implementation was understood; business behavior was unchanged by that cleanup.

## Design decisions

- Planning remains deterministic and does not call an LLM.
- `DeterministicGoalPlanner` receives prerequisite data and item duration through dependency injection.
- The planner consumes `LearnerState` without loading, saving, or mutating it.
- `PlanningOrchestrator` owns the application-level read-plan-save workflow.
- The orchestrator uses `model_copy(deep=True)` before assigning `active_plan`.
- Persistence is accessed through the `LearnerRepository` protocol rather than directly from planning code.
- Learner state is stored as a complete JSON snapshot and validated with Pydantic when loaded.
- A single repository save uses one SQLAlchemy transaction and therefore commits or rolls back as a unit.
- Synchronous SQLAlchemy operations run through `asyncio.to_thread()` so they do not block the FastAPI event loop.
- FastAPI lifespan management creates shared dependencies at startup and disposes database engines at shutdown.

## Files changed

- `.env.example`
- `apps/api/main.py`
- `src/goalcoach/agents/goal_planning.py`
- `src/goalcoach/infrastructure/config.py`
- `src/goalcoach/infrastructure/persistence/__init__.py`
- `src/goalcoach/infrastructure/persistence/database.py`
- `src/goalcoach/infrastructure/persistence/models.py`
- `src/goalcoach/infrastructure/persistence/repositories.py`
- `src/goalcoach/ui/orchestrator.py`
- `tests/integration/test_content_repository.py`
- `tests/integration/test_learner_repository.py`
- `tests/unit/test_config.py`
- `tests/unit/test_goal_planning.py`
- `tests/unit/test_orchestrator.py`

## Tests

```bash
.venv/bin/python -m pytest -q
```

Result:

```text
58 passed
```

The tests verify:

- all 18 prerequisite relationships are loaded from the content database;
- a new concept remains blocked until its prerequisites have evidence and sufficient mastery;
- invalid prerequisite configuration fails fast;
- configurable item duration is validated and injected into the planner;
- the orchestrator assigns the plan to a copied learner state;
- the original learner state remains unmodified;
- learner snapshots survive database round trips and replace the previous snapshot;
- an unknown learner produces the expected application error;
- the existing `REVIEW -> REMEDIAL -> NEW` behavior remains intact.

Static verification:

```bash
.venv/bin/python -m ruff check \
  apps/api/main.py \
  src/goalcoach/agents/goal_planning.py \
  src/goalcoach/infrastructure/config.py \
  src/goalcoach/infrastructure/persistence \
  src/goalcoach/ui/orchestrator.py
```

Result:

```text
All checks passed!
```

## Jira scope

| Issue | Scope in this phase | Status |
|---|---|---|
| [GCO-14](https://psyche97.atlassian.net/browse/GCO-14) | Parent Goal Planning task | Complete across both phases |
| [GCO-63](https://psyche97.atlassian.net/browse/GCO-63) | Prerequisite-aware concept selection | Complete |
| [GCO-67](https://psyche97.atlassian.net/browse/GCO-67) | Read learner state | Complete |
| Orchestrator handoff | Assign and persist `active_plan` | Complete |
| Configurable item duration | Replace fixed five-minute allocation | Complete |

## Not included / follow-up work

- Add optimistic concurrency control before multiple requests update the same learner simultaneously.
- Connect the answer, grading, mastery-update, and automatic re-planning loop.
- Validate the mastery thresholds and item-duration default with product evidence.
- Add a full API-to-database end-to-end test for plan generation.

## Reviewer checklist

- [x] Reuses the existing Pydantic domain contracts.
- [x] Preserves the existing `GoalPlanner` and `LearnerRepository` protocols.
- [x] Validates all 18 curriculum prerequisite relationships.
- [x] Prevents infeasible `NEW` concept selection.
- [x] Preserves deterministic, zero-LLM planning.
- [x] Does not mutate the planner's input `LearnerState`.
- [x] Assigns the generated plan to `active_plan` in the orchestration layer.
- [x] Persists the updated learner aggregate atomically.
- [x] Makes item duration configuration-driven.
- [x] Adds focused unit and integration tests.
- [x] Does not include secrets, generated databases, or personal learner data.

## Suggested PR title

```text
feat(planning): complete prerequisite-aware orchestration and persistence
```

> This phase implements GCO-63 and GCO-67 and completes the prerequisite, orchestration, persistence, and configuration follow-up work for GCO-14.


[GCO-14]: https://psyche97.atlassian.net/browse/GCO-14?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
