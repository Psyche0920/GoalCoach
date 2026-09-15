from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import exists, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from goalcoach.domain.models import LearnerState, LearningEvent, TeachingSession
from goalcoach.infrastructure.persistence.learner_models import (
    LearnerStateORM,
    LearningEventORM,
    TeachingSessionORM,
)
from goalcoach.infrastructure.persistence.models import (
    ConceptPrerequisite,
    ContentExercise,
    CurriculumConcept,
    TeachingCard,
)

logger = logging.getLogger(__name__)


class LearnerRepositoryError(RuntimeError):
    """Raised when a learner aggregate cannot be loaded or persisted."""


class TeachingSessionRepositoryError(RuntimeError):
    """Raised when a teaching session cannot be loaded or persisted."""


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

    def get_concept(self, concept_id: str) -> CurriculumConcept | None:
        clean_id = concept_id.strip()
        statement = (
            select(CurriculumConcept)
            .where(
                (CurriculumConcept.concept_id == clean_id)
                | (CurriculumConcept.slug == clean_id)
                | (CurriculumConcept.title_en.ilike(f"%{clean_id}%")),
                CurriculumConcept.is_active.is_(True),
            )
            .limit(1)
        )
        with self._session_factory() as session:
            return session.scalars(statement).first()

    def list_cards_for_concept(self, concept_id: str) -> list[TeachingCard]:
        return self.get_teaching_cards(concept_id)

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

    def get_exercise(self, exercise_id: str) -> ContentExercise | None:
        """Lookup an exercise by its unique content ID."""
        statement = (
            select(ContentExercise)
            .where(ContentExercise.exercise_id == exercise_id)
            .limit(1)
        )
        with self._session_factory() as session:
            return session.scalars(statement).first()

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

    async def get(self, learner_id: UUID | str) -> LearnerState | None:
        """Load and validate a learner aggregate without blocking the event loop."""
        return await asyncio.to_thread(self._get_sync, learner_id)

    async def save(self, state: LearnerState) -> None:
        """Insert or replace one aggregate in a single database transaction."""
        snapshot = state.model_dump(mode="json")
        await asyncio.to_thread(self._save_sync, state, snapshot)

    async def record_learning_event(self, event: LearningEvent) -> None:
        """Record an immutable learning event into the audit log."""
        await asyncio.to_thread(self._record_learning_event_sync, event)

    async def get_learning_events(
        self, learner_id: UUID | str, limit: int = 100
    ) -> list[LearningEvent]:
        """Fetch chronological learning events for a learner."""
        return await asyncio.to_thread(self._get_learning_events_sync, learner_id, limit)

    def _get_sync(self, learner_id: UUID | str) -> LearnerState | None:
        try:
            with self._session_factory() as session:
                record = session.get(LearnerStateORM, str(learner_id))
                if record is None:
                    return None
                return LearnerState.model_validate(record.state_json)
        except (SQLAlchemyError, ValidationError) as exc:
            logger.exception("Failed to load learner state", extra={"learner_id": str(learner_id)})
            raise LearnerRepositoryError(f"Failed to load learner {learner_id}") from exc

    def _save_sync(self, state: LearnerState, snapshot: dict[str, object]) -> None:
        try:
            with self._session_factory.begin() as session:
                record = session.get(LearnerStateORM, str(state.learner_id))
                if record is None:
                    session.add(
                        LearnerStateORM(
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

    def _record_learning_event_sync(self, event: LearningEvent) -> None:
        try:
            with self._session_factory.begin() as session:
                session.add(
                    LearningEventORM(
                        id=event.id,
                        learner_id=str(event.learner_id),
                        plan_item_id=str(event.plan_item_id),
                        concept_ids=list(event.concept_ids),
                        event_type=event.event_type,
                        started_at=event.started_at,
                        active_seconds=event.active_seconds,
                        engagement_score=event.engagement_score,
                        grading_result=event.grading_result,
                        created_at=event.created_at,
                    )
                )
        except SQLAlchemyError as exc:
            logger.exception("Failed to record learning event", extra={"event_id": event.id})
            raise LearnerRepositoryError(f"Failed to record event {event.id}") from exc

    def _get_learning_events_sync(
        self, learner_id: UUID | str, limit: int = 100
    ) -> list[LearningEvent]:
        try:
            statement = (
                select(LearningEventORM)
                .where(LearningEventORM.learner_id == str(learner_id))
                .order_by(LearningEventORM.created_at.desc())
                .limit(limit)
            )
            with self._session_factory() as session:
                records = list(session.scalars(statement))
                return [
                    LearningEvent(
                        id=r.id,
                        learner_id=r.learner_id,
                        plan_item_id=r.plan_item_id,
                        concept_ids=r.concept_ids,
                        event_type=r.event_type,  # type: ignore[arg-type]
                        started_at=r.started_at,
                        active_seconds=r.active_seconds,
                        engagement_score=r.engagement_score,
                        grading_result=r.grading_result,
                        created_at=r.created_at,
                    )
                    for r in records
                ]
        except SQLAlchemyError as exc:
            logger.exception(
                "Failed to load learning events", extra={"learner_id": str(learner_id)}
            )
            raise LearnerRepositoryError(f"Failed to load events for {learner_id}") from exc


SqliteLearnerRepository = SqlAlchemyLearnerRepository


class SqlAlchemyTeachingSessionRepository:
    """Persist complete teaching sessions as validated JSON snapshots."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    async def get(self, session_id: UUID | str) -> TeachingSession | None:
        return await asyncio.to_thread(self._get_sync, session_id)

    async def save(self, teaching_session: TeachingSession) -> None:
        snapshot = teaching_session.model_dump(mode="json")
        await asyncio.to_thread(self._save_sync, teaching_session, snapshot)

    async def save_transition(
        self,
        learner: LearnerState,
        event: LearningEvent,
        teaching_session: TeachingSession,
    ) -> None:
        """Atomically persist learner, audit event, and teaching session."""
        await asyncio.to_thread(
            self._save_transition_sync,
            learner,
            event,
            teaching_session,
        )

    def _get_sync(self, session_id: UUID | str) -> TeachingSession | None:
        try:
            with self._session_factory() as database_session:
                record = database_session.get(TeachingSessionORM, str(session_id))
                if record is None:
                    return None
                return TeachingSession.model_validate(record.session_json)
        except (SQLAlchemyError, ValidationError) as exc:
            logger.exception(
                "Failed to load teaching session",
                extra={"session_id": str(session_id)},
            )
            raise TeachingSessionRepositoryError(
                f"Failed to load teaching session {session_id}"
            ) from exc

    def _save_sync(
        self,
        teaching_session: TeachingSession,
        snapshot: dict[str, object],
    ) -> None:
        try:
            with self._session_factory.begin() as database_session:
                record = database_session.get(
                    TeachingSessionORM,
                    str(teaching_session.id),
                )
                if record is None:
                    database_session.add(
                        TeachingSessionORM(
                            session_id=str(teaching_session.id),
                            learner_id=str(teaching_session.learner_id),
                            session_json=snapshot,
                            updated_at=teaching_session.updated_at,
                        )
                    )
                else:
                    record.session_json = snapshot
                    record.updated_at = teaching_session.updated_at
        except SQLAlchemyError as exc:
            logger.exception(
                "Failed to save teaching session",
                extra={"session_id": str(teaching_session.id)},
            )
            raise TeachingSessionRepositoryError(
                f"Failed to save teaching session {teaching_session.id}"
            ) from exc

    def _save_transition_sync(
        self,
        learner: LearnerState,
        event: LearningEvent,
        teaching_session: TeachingSession,
    ) -> None:
        try:
            with self._session_factory.begin() as database_session:
                learner_record = database_session.get(
                    LearnerStateORM,
                    str(learner.learner_id),
                )
                learner_snapshot = learner.model_dump(mode="json")
                if learner_record is None:
                    database_session.add(
                        LearnerStateORM(
                            learner_id=str(learner.learner_id),
                            state_json=learner_snapshot,
                            updated_at=learner.updated_at,
                        )
                    )
                else:
                    learner_record.state_json = learner_snapshot
                    learner_record.updated_at = learner.updated_at

                database_session.add(
                    LearningEventORM(
                        id=event.id,
                        learner_id=str(event.learner_id),
                        plan_item_id=str(event.plan_item_id),
                        concept_ids=list(event.concept_ids),
                        event_type=event.event_type,
                        started_at=event.started_at,
                        active_seconds=event.active_seconds,
                        engagement_score=event.engagement_score,
                        grading_result=event.grading_result,
                        created_at=event.created_at,
                    )
                )

                session_record = database_session.get(
                    TeachingSessionORM,
                    str(teaching_session.id),
                )
                session_snapshot = teaching_session.model_dump(mode="json")
                if session_record is None:
                    database_session.add(
                        TeachingSessionORM(
                            session_id=str(teaching_session.id),
                            learner_id=str(teaching_session.learner_id),
                            session_json=session_snapshot,
                            updated_at=teaching_session.updated_at,
                        )
                    )
                else:
                    session_record.session_json = session_snapshot
                    session_record.updated_at = teaching_session.updated_at
        except SQLAlchemyError as exc:
            logger.exception(
                "Failed to save teaching transition",
                extra={"session_id": str(teaching_session.id), "event_id": event.id},
            )
            raise TeachingSessionRepositoryError(
                f"Failed to save transition for session {teaching_session.id}"
            ) from exc
