# GCO-63 and GCO-67 Planning Integration

## Summary

This work completes prerequisite-aware concept selection and connects deterministic daily-plan generation to learner-state persistence.

The application now reads the current `LearnerState`, generates a prerequisite-safe `DailyPlan`, assigns the plan to a copied learner aggregate, and atomically persists the updated state. Planning remains deterministic and does not invoke an LLM.

---

## Scope completed

### GCO-63: Prerequisite-aware concept selection

When the planner selects a `NEW` concept, it now checks the prerequisite relationships stored in `goalcoach_hsk1_learning.db`.

A new concept is eligible only when every required prerequisite:

- exists in `LearnerState.mastery`;
- has at least one item of learning evidence;
- meets the configured mastery threshold.

Invalid prerequisite configuration, including unknown concepts and self-dependencies, fails fast during planner construction.

The existing planning priority remains:

```text
REVIEW -> REMEDIAL -> NEW
```

### GCO-67: Learner-state read and persistence handoff

The planner continues to treat its input `LearnerState` as read-only. The application-level orchestrator now owns the state transition:

```text
Load LearnerState
    -> Create DailyPlan
    -> Deep-copy LearnerState
    -> Assign active_plan
    -> Update updated_at
    -> Persist the complete aggregate
```

The original state object is not mutated.

### Configurable planning item duration

The previous fixed five-minute allocation is now supplied through application settings:

```text
GOALCOACH_PLANNING_ITEM_MINUTES=5
```

The default remains five minutes, while deployments and tests can provide a different validated value.

---

## Architecture and design decisions

- **Deterministic planning:** prerequisite checks, prioritization, and time allocation are implemented as rules rather than LLM calls.
- **Dependency injection:** prerequisite data and item duration are injected into `DeterministicGoalPlanner` at application startup.
- **Domain immutability:** `PlanningOrchestrator` creates a deep copy before assigning `active_plan`.
- **Repository boundary:** orchestration depends on the `LearnerRepository` protocol rather than SQLAlchemy directly.
- **Boundary validation:** persisted JSON is rebuilt through `LearnerState.model_validate()` when loaded.
- **Atomic persistence:** a learner snapshot and its timestamp are inserted or updated in one SQLAlchemy transaction.
- **Resource cleanup:** application lifespan management disposes both database engines during shutdown.
- **Failure translation:** persistence failures are exposed through `LearnerRepositoryError`; the API maps missing learners to HTTP 404 and storage failures to HTTP 503.

### Trade-offs

- Learner state is stored as one complete JSON snapshot. This makes aggregate replacement simple and atomic, but is less suitable for querying individual nested fields.
- The current SQLAlchemy driver is synchronous, so learner repository calls use `asyncio.to_thread()` to avoid blocking the FastAPI event loop. A native asynchronous driver may be preferable at higher concurrency.
- A single save is atomic, but the complete read-plan-save sequence does not yet use optimistic locking. Concurrent updates to the same learner could overwrite each other.

---

## Files changed

### Planning

- `src/goalcoach/agents/goal_planning.py`
  - validates prerequisite configuration;
  - filters infeasible `NEW` concepts;
  - accepts configurable item duration and mastery thresholds.

### Persistence

- `src/goalcoach/infrastructure/persistence/models.py`
  - defines `LearnerStateRecord` for complete learner-state snapshots.
- `src/goalcoach/infrastructure/persistence/repositories.py`
  - adds curriculum prerequisite lookup;
  - implements learner-state load and atomic save operations;
  - translates SQLAlchemy and Pydantic failures into a repository-specific exception.
- `src/goalcoach/infrastructure/persistence/database.py`
  - exposes the bound engine;
  - creates only the learner-state table in the learner database.
- `src/goalcoach/infrastructure/persistence/__init__.py`
  - exports the persistence components used by the application.

### Application integration

- `src/goalcoach/ui/orchestrator.py`
  - coordinates read, plan, copy, and save operations.
- `apps/api/main.py`
  - builds repositories and the planner during application startup;
  - injects prerequisite data from the content database;
  - exposes learner retrieval and daily-plan generation endpoints;
  - disposes database engines during shutdown.

### Configuration

- `src/goalcoach/infrastructure/config.py`
  - adds validated `planning_item_minutes` configuration.
- `.env.example`
  - documents `GOALCOACH_PLANNING_ITEM_MINUTES`.

### Tests

- `tests/unit/test_goal_planning.py`
- `tests/unit/test_orchestrator.py`
- `tests/unit/test_config.py`
- `tests/integration/test_content_repository.py`
- `tests/integration/test_learner_repository.py`

---

## API behavior

### Read learner state

```text
GET /api/v1/learners/{learner_id}
```

- returns the validated learner state when found;
- returns `404` when the learner does not exist;
- returns `503` when persistence is unavailable.

### Generate and persist a daily plan

```text
POST /api/v1/learners/{learner_id}/plans
```

- loads the learner state;
- creates a deterministic prerequisite-aware plan;
- persists the plan in `state.active_plan`;
- returns the generated plan with HTTP `201`.

---

## Verification

Run the complete test suite:

```bash
.venv/bin/python -m pytest -q
```

Verified result:

```text
58 passed
```

Run focused tests:

```bash
.venv/bin/python -m pytest \
  tests/unit/test_goal_planning.py \
  tests/unit/test_orchestrator.py \
  tests/unit/test_config.py \
  tests/integration/test_content_repository.py \
  tests/integration/test_learner_repository.py -v
```

Run static checks for the implementation files:

```bash
.venv/bin/python -m ruff check \
  apps/api/main.py \
  src/goalcoach/agents/goal_planning.py \
  src/goalcoach/infrastructure/config.py \
  src/goalcoach/infrastructure/persistence \
  src/goalcoach/ui/orchestrator.py
```

---

## Completion status

| Work item | Result |
|---|---|
| GCO-63 prerequisite checking | Complete |
| GCO-67 learner-state repository read | Complete |
| Orchestrator persistence handoff | Complete |
| Configurable item duration | Complete |
| Zero-LLM deterministic planning | Preserved |
| Input `LearnerState` mutation | None |

## Remaining engineering work

- Add optimistic concurrency control before multiple requests can update the same learner concurrently.
- Connect the answer, grading, mastery-update, and re-planning loop.
- Validate planning thresholds and duration defaults with product evidence.
