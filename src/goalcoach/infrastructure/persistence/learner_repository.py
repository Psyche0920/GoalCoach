"""SQLite learner state persistence interface with WAL mode guarantees."""

from __future__ import annotations

from goalcoach.infrastructure.persistence.database import (
    create_learner_schema,
    create_session_factory,
)
from goalcoach.infrastructure.persistence.repositories import (
    LearnerRepositoryError,
    SqlAlchemyLearnerRepository,
    SqliteLearnerRepository,
)


def create_learner_repository(database_url: str) -> SqliteLearnerRepository:
    """Initialize SQLite session factory with WAL mode and ensure table schema exists."""
    session_factory = create_session_factory(database_url)
    create_learner_schema(session_factory)
    return SqliteLearnerRepository(session_factory)


__all__ = [
    "LearnerRepositoryError",
    "SqlAlchemyLearnerRepository",
    "SqliteLearnerRepository",
    "create_learner_repository",
]
