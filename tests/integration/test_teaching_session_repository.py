"""Integration coverage for durable teaching session snapshots."""

from pathlib import Path

import pytest

from goalcoach.domain.models import (
    Exercise,
    LearnerState,
    LearningEvent,
    TeachingAction,
    TeachingSession,
)
from goalcoach.infrastructure.persistence.database import (
    create_learner_schema,
    create_session_factory,
)
from goalcoach.infrastructure.persistence.repositories import (
    SqlAlchemyLearnerRepository,
    SqlAlchemyTeachingSessionRepository,
)


@pytest.mark.asyncio
async def test_repository_round_trips_pending_action(tmp_path: Path) -> None:
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'sessions.db'}")
    create_learner_schema(session_factory)
    repository = SqlAlchemyTeachingSessionRepository(session_factory)
    pending_action = TeachingAction(
        action_type="ask",
        concept_id="hsk1_c20",
        content="请试一试。",
        objective="Check ability expression.",
        expected_response=True,
        exercise=Exercise(
            id="exercise-1",
            concept_id="hsk1_c20",
            prompt="请用‘会’造句。",
            target_instruction="Use 会 to describe an ability.",
            reference_answers=["她会说汉语。"],
        ),
    )
    teaching_session = TeachingSession(
        learner_id="learner-1",
        concept_id="hsk1_c20",
        pending_action=pending_action,
    )

    await repository.save(teaching_session)
    loaded = await repository.get(teaching_session.id)

    assert loaded is not None
    assert loaded.id == teaching_session.id
    assert loaded.pending_action == pending_action


@pytest.mark.asyncio
async def test_transition_atomically_persists_all_aggregates(tmp_path: Path) -> None:
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'transition.db'}")
    create_learner_schema(session_factory)
    sessions = SqlAlchemyTeachingSessionRepository(session_factory)
    learners = SqlAlchemyLearnerRepository(session_factory)
    learner = LearnerState(learner_id="learner-1", state_version=2)
    teaching_session = TeachingSession(
        learner_id=learner.learner_id,
        concept_id="hsk1_c20",
    )
    event = LearningEvent(
        id="event-1",
        learner_id="learner-1",
        plan_item_id="exercise-1",
        concept_ids=["hsk1_c20"],
        event_type="attempt",
    )

    await sessions.save_transition(learner, event, teaching_session)

    loaded_learner = await learners.get(learner.learner_id)
    loaded_session = await sessions.get(teaching_session.id)
    loaded_events = await learners.get_learning_events(learner.learner_id)
    assert loaded_learner is not None
    assert loaded_learner.state_version == 2
    assert loaded_session is not None
    assert loaded_events[0].id == event.id
