from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import exists, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from goalcoach.domain.models import LearnerState
from goalcoach.infrastructure.persistence.models import (
    ConceptPrerequisite,
    ContentExercise,
    CurriculumConcept,
    LearnerStateRecord,
    TeachingCard,
)

logger = logging.getLogger(__name__)


class LearnerRepositoryError(RuntimeError):
    """Raised when a learner aggregate cannot be loaded or persisted."""


class ContentRepository:
    """Query curriculum content through SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_concepts(self, hsk_level: int = 1) -> list[CurriculumConcept]:
        statement = (
            select(CurriculumConcept)
            .where(
                CurriculumConcept.hsk_level == hsk_level,
                CurriculumConcept.is_active.is_(True),
            )
            .order_by(CurriculumConcept.sequence_no)
        )
        with self._session_factory() as session:
            return list(session.scalars(statement))

    def get_teaching_cards(self, concept_id: str) -> list[TeachingCard]:
        statement = (
            select(TeachingCard)
            .join(TeachingCard.concept)
            .where(
                TeachingCard.concept_id == concept_id,
                CurriculumConcept.is_active.is_(True),
            )
            .order_by(TeachingCard.card_order)
        )
        with self._session_factory() as session:
            return list(session.scalars(statement))

    def get_exercises(
        self, concept_id: str, *, limit: int = 3, randomize: bool = True
    ) -> list[ContentExercise]:
        order = func.random() if randomize else ContentExercise.exercise_order
        statement = (
            select(ContentExercise)
            .join(ContentExercise.concept)
            .where(
                ContentExercise.concept_id == concept_id,
                CurriculumConcept.is_active.is_(True),
            )
            .order_by(order)
            .limit(limit)
        )
        with self._session_factory() as session:
            return list(session.scalars(statement))

    def get_remedial_exercises(self, error_tag: str, *, limit: int = 5) -> list[ContentExercise]:
        error_tags = func.json_each(ContentExercise.error_tags).table_valued("key", "value")
        statement = (
            select(ContentExercise)
            .join(ContentExercise.concept)
            .where(
                exists(select(1).select_from(error_tags).where(error_tags.c.value == error_tag)),
                CurriculumConcept.is_active.is_(True),
            )
            .order_by(func.random())
            .limit(limit)
        )
        with self._session_factory() as session:
            return list(session.scalars(statement))

    def get_prerequisites(self) -> dict[str, frozenset[str]]:
        """Return prerequisite concept IDs grouped by target concept."""
        statement = select(ConceptPrerequisite).order_by(
            ConceptPrerequisite.concept_id,
            ConceptPrerequisite.prerequisite_id,
        )
        grouped: dict[str, set[str]] = {}
        with self._session_factory() as session:
            for rule in session.scalars(statement):
                grouped.setdefault(rule.concept_id, set()).add(rule.prerequisite_id)
        return {
            concept_id: frozenset(prerequisite_ids)
            for concept_id, prerequisite_ids in grouped.items()
        }


class SqlAlchemyLearnerRepository:
    """Persist complete learner aggregates as validated JSON snapshots."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    async def get(self, learner_id: UUID) -> LearnerState | None:
        """Load and validate a learner aggregate without blocking the event loop."""
        return await asyncio.to_thread(self._get_sync, learner_id)

    async def save(self, state: LearnerState) -> None:
        """Insert or replace one aggregate in a single database transaction."""
        snapshot = state.model_dump(mode="json")
        await asyncio.to_thread(self._save_sync, state, snapshot)

    def _get_sync(self, learner_id: UUID) -> LearnerState | None:
        try:
            with self._session_factory() as session:
                record = session.get(LearnerStateRecord, str(learner_id))
                if record is None:
                    return None
                return LearnerState.model_validate(record.state_json)
        except (SQLAlchemyError, ValidationError) as exc:
            logger.exception("Failed to load learner state", extra={"learner_id": str(learner_id)})
            raise LearnerRepositoryError(f"Failed to load learner {learner_id}") from exc

    def _save_sync(self, state: LearnerState, snapshot: dict[str, object]) -> None:
        try:
            with self._session_factory.begin() as session:
                record = session.get(LearnerStateRecord, str(state.learner_id))
                if record is None:
                    session.add(
                        LearnerStateRecord(
                            learner_id=str(state.learner_id),
                            state_json=snapshot,
                            updated_at=state.updated_at,
                        )
                    )
                else:
                    record.state_json = snapshot
                    record.updated_at = state.updated_at
        except SQLAlchemyError as exc:
            logger.exception(
                "Failed to save learner state", extra={"learner_id": str(state.learner_id)}
            )
            raise LearnerRepositoryError(f"Failed to save learner {state.learner_id}") from exc
