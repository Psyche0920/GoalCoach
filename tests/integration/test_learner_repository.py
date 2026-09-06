"""Integration coverage for durable learner aggregate snapshots."""

from pathlib import Path

import pytest

from goalcoach.domain.models import LearnerState, LearningGoal
from goalcoach.infrastructure.persistence import (
    SqlAlchemyLearnerRepository,
    create_learner_schema,
    create_session_factory,
)


@pytest.mark.asyncio
async def test_repository_round_trips_and_replaces_learner_state(tmp_path: Path) -> None:
    database_path = tmp_path / "learners.db"
    session_factory = create_session_factory(f"sqlite:///{database_path}")
    create_learner_schema(session_factory)
    repository = SqlAlchemyLearnerRepository(session_factory)
    state = LearnerState(goal=LearningGoal(title="Complete HSK 1", target_hsk_level=1))

    await repository.save(state)
    loaded = await repository.get(state.learner_id)

    assert loaded == state

    replacement = state.model_copy(update={"goal_changed": True}, deep=True)
    await repository.save(replacement)
    reloaded = await repository.get(state.learner_id)

    assert reloaded is not None
    assert reloaded.goal_changed is True
