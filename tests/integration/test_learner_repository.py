"""Integration coverage for durable learner aggregate snapshots."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from goalcoach.domain.models import LearnerState, LearningEvent, LearningGoal
from goalcoach.infrastructure.persistence import (
    SqlAlchemyLearnerRepository,
    create_learner_schema,
    create_session_factory,
)
from goalcoach.infrastructure.persistence.repositories import StaleLearnerStateError


@pytest.mark.asyncio
async def test_repository_round_trips_and_replaces_learner_state(tmp_path: Path) -> None:
    database_path = tmp_path / "learners.db"
    session_factory = create_session_factory(f"sqlite:///{database_path}")
    create_learner_schema(session_factory)
    repository = SqlAlchemyLearnerRepository(session_factory)
    state = LearnerState(goal=LearningGoal(title="Complete HSK 1", target_hsk_level=1))

    await repository.save(state)
    loaded = await repository.get(state.learner_id)

    assert loaded is not None
    assert loaded.learner_id == state.learner_id
    assert loaded.goal == state.goal
    assert loaded.state_version == state.state_version

    replacement = state.model_copy(update={"goal_changed": True}, deep=True)
    await repository.save(replacement)
    reloaded = await repository.get(state.learner_id)

    assert reloaded is not None
    assert reloaded.goal_changed is True


@pytest.mark.asyncio
async def test_optimistic_lock_rejects_parallel_writer(tmp_path: Path) -> None:
    database_path = tmp_path / "learners.db"
    session_factory = create_session_factory(f"sqlite:///{database_path}")
    create_learner_schema(session_factory)
    repository = SqlAlchemyLearnerRepository(session_factory)
    state = LearnerState()
    stale = state.model_copy(deep=True)

    await repository.save(state)

    assert state.state_version == 2
    with pytest.raises(StaleLearnerStateError):
        await repository.save(stale)

    reloaded = await repository.get(state.learner_id)
    assert reloaded is not None
    assert reloaded.goal_changed is False


@pytest.mark.asyncio
async def test_state_and_learning_event_commit_atomically(tmp_path: Path) -> None:
    database_path = tmp_path / "learners.db"
    session_factory = create_session_factory(f"sqlite:///{database_path}")
    create_learner_schema(session_factory)
    repository = SqlAlchemyLearnerRepository(session_factory)
    state = LearnerState()
    event = LearningEvent(
        learner_id=str(state.learner_id),
        plan_item_id="plan-item",
        event_type="attempt",
    )

    await repository.save(state)
    state.goal_changed = True
    await repository.save_with_event(state, event)

    reloaded = await repository.get(state.learner_id)
    events = await repository.get_learning_events(state.learner_id)
    assert reloaded is not None
    assert reloaded.goal_changed is True
    assert reloaded.state_version == 3
    assert state.state_version == 3
    assert [item.id for item in events] == [event.id]


@pytest.mark.asyncio
async def test_legacy_database_backfills_optimistic_version(tmp_path: Path) -> None:
    """Legacy rows keep their JSON version so the next authoritative write is accepted."""
    database_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE learner_states (
                learner_id VARCHAR(64) PRIMARY KEY,
                state_json JSON NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL
            )
        """))
        connection.execute(text("""
            INSERT INTO learner_states (learner_id, state_json, updated_at)
            VALUES (:learner_id, :state_json, CURRENT_TIMESTAMP)
        """), {
            "learner_id": "legacy-learner",
            "state_json": '{"learner_id": "legacy-learner", "state_version": 7}',
        })

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    create_learner_schema(session_factory)
    columns = {column["name"] for column in inspect(engine).get_columns("learner_states")}
    assert "state_version" in columns

    repository = SqlAlchemyLearnerRepository(session_factory)
    state = await repository.get("legacy-learner")
    assert state is not None and state.state_version == 7

    state.goal_changed = True
    await repository.save(state)
    reloaded = await repository.get("legacy-learner")
    assert reloaded is not None
    assert reloaded.state_version == 8
