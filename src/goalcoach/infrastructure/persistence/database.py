from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from goalcoach.infrastructure.persistence.learner_models import LearnerBase


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    """Create the SQLAlchemy engine and session factory used by repositories."""

    engine = create_engine(database_url)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragmas(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return sessionmaker(bind=engine, expire_on_commit=False)


def get_engine(session_factory: sessionmaker[Session]) -> Engine:
    """Return the engine bound to a session factory."""

    engine = session_factory.kw.get("bind")
    if not isinstance(engine, Engine):
        raise TypeError("The session factory is not bound to an engine")
    return engine


def create_learner_schema(session_factory: sessionmaker[Session]) -> None:
    """Create all learner state and audit tables in the configured database."""
    LearnerBase.metadata.create_all(
        bind=get_engine(session_factory),
        checkfirst=True,
    )
