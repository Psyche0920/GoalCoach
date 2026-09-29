import logging
import time

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.persistence.learner_models import LearnerBase

logger = logging.getLogger("goalcoach.persistence.database")


def create_session_factory(
    database_url: str,
    slow_query_threshold_ms: float | None = None,
) -> sessionmaker[Session]:
    """Create the SQLAlchemy engine and session factory used by repositories."""
    threshold = (
        slow_query_threshold_ms
        if slow_query_threshold_ms is not None
        else Settings().log_slow_query_threshold_ms
    )
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

    db_target = (
        "content"
        if ("learning.db" in database_url or "database1" in database_url)
        else "learner_state"
    )

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(
        _conn: object,
        _cursor: object,
        _statement: str,
        _parameters: object,
        context: object,
        _executemany: bool,
    ) -> None:
        if context is not None:
            context._query_start_time = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(
        _conn: object,
        cursor: object,
        statement: str,
        _parameters: object,
        context: object,
        _executemany: bool,
    ) -> None:
        start_time = getattr(context, "_query_start_time", None) if context else None
        duration_ms = (time.perf_counter() - start_time) * 1000 if start_time else 0.0

        statement_clean = statement.strip() if statement else ""
        statement_type = statement_clean.split(None, 1)[0].upper() if statement_clean else "UNKNOWN"
        row_count = getattr(cursor, "rowcount", -1)

        telemetry = {
            "db.system": "sqlite",
            "db.name": db_target,
            "statement_type": statement_type,
            "duration_ms": round(duration_ms, 2),
            "row_count": row_count,
        }

        if duration_ms > threshold:
            logger.warning(
                "Slow SQLite query on %s (%s, %.2fms): %s",
                db_target,
                statement_type,
                duration_ms,
                statement_clean[:120],
                extra={"extra": telemetry},
            )
        else:
            logger.debug(
                "SQLite query on %s (%s, %.2fms)",
                db_target,
                statement_type,
                duration_ms,
                extra={"extra": telemetry},
            )

    @event.listens_for(engine, "handle_error")
    def handle_error(exception_context: object) -> None:
        orig = getattr(exception_context, "original_exception", "Unknown DB error")
        stmt = getattr(exception_context, "statement", None)
        logger.error(
            "SQLite query error on %s: %s",
            db_target,
            orig,
            extra={
                "extra": {
                    "db.system": "sqlite",
                    "db.name": db_target,
                    "statement": str(stmt)[:200] if stmt else None,
                }
            },
        )

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
                text(
                    "ALTER TABLE learner_states ADD COLUMN state_version INTEGER NOT NULL DEFAULT 1"
                )
            )
            connection.execute(
                text("""
                    UPDATE learner_states
                    SET state_version = CAST(JSON_EXTRACT(state_json, '$.state_version') AS INTEGER)
                    WHERE JSON_VALID(state_json)
                      AND JSON_EXTRACT(state_json, '$.state_version') IS NOT NULL
                """)
            )
