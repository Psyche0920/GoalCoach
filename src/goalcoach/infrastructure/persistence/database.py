from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    """Create the SQLAlchemy engine and session factory used by repositories."""

    engine = create_engine(database_url)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return sessionmaker(bind=engine, expire_on_commit=False)


def get_engine(session_factory: sessionmaker[Session]) -> Engine:
    """Return the engine bound to a session factory."""

    engine = session_factory.kw.get("bind")
    if not isinstance(engine, Engine):
        raise RuntimeError("The session factory is not bound to an engine")
    return engine
