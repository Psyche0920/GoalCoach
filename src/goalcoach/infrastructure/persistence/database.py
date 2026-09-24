from __future__ import annotations

from sqlalchemy import Engine, create_engine, event, inspect, text
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
    engine = get_engine(session_factory)
    LearnerBase.metadata.create_all(
        bind=engine,
        checkfirst=True,
    )
    inspector = inspect(engine)
    learner_columns = {column["name"] for column in inspector.get_columns("learner_states")}
    if "state_version" not in learner_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE learner_states ADD COLUMN state_version INTEGER NOT NULL DEFAULT 1")
            )
            connection.execute(
                text("""
                    UPDATE learner_states
                    SET state_version = CAST(JSON_EXTRACT(state_json, '$.state_version') AS INTEGER)
                    WHERE JSON_VALID(state_json)
                      AND JSON_EXTRACT(state_json, '$.state_version') IS NOT NULL
                """)
            )
