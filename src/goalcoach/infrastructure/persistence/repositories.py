from __future__ import annotations

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, sessionmaker

from goalcoach.infrastructure.persistence.models import (
    ContentExercise,
    CurriculumConcept,
    TeachingCard,
)


class ContentRepository:
    """Queries Database #1 through SQLAlchemy instead of ``sqlite3``."""

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

    def get_remedial_exercises(
        self, error_tag: str, *, limit: int = 5
    ) -> list[ContentExercise]:
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
