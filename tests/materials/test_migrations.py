"""Populated historical database migrations and stale-run ownership regressions."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from test_batch_publication import packet

from goalcoach.materials.models import Catalog, GateError, Packet, StorageError
from goalcoach.materials.store import SCHEMA, Workbench

LEGACY_TABLES = ("sources", "spans", "runs", "tasks", "versions", "approvals", "releases", "audit")
LEGACY_RUN = "legacy-run"
LEGACY_TASK = "legacy-catalog-task"
LEGACY_V2_UPGRADE = """
ALTER TABLE releases RENAME TO releases_v1;
CREATE TABLE releases(id TEXT PRIMARY KEY,version_id TEXT NOT NULL REFERENCES versions(id),path TEXT NOT NULL,state TEXT NOT NULL);
INSERT INTO releases SELECT * FROM releases_v1;
DROP TABLE releases_v1;
CREATE TABLE release_versions(release_id TEXT NOT NULL REFERENCES releases(id),version_id TEXT NOT NULL REFERENCES versions(id),sequence_no INTEGER NOT NULL CHECK(sequence_no>0),PRIMARY KEY(release_id,version_id),UNIQUE(release_id,sequence_no));
INSERT INTO release_versions SELECT id,version_id,1 FROM releases;
CREATE TABLE task_attempts(owner TEXT PRIMARY KEY,task_key TEXT NOT NULL REFERENCES tasks(key),run_id TEXT NOT NULL REFERENCES runs(id),outcome TEXT NOT NULL,usage_json TEXT,started_at REAL NOT NULL);
DROP TABLE schema_version;
CREATE TABLE schema_version(version INTEGER PRIMARY KEY CHECK(version=2));
INSERT INTO schema_version VALUES(2);
"""


def create_legacy_database(path: Path, schema_version: int = 1) -> Packet:
    """Build the actual historical schema without invoking the migrator under test."""
    value = packet("legacy-concept")
    version_id = value.digest()
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(SCHEMA)
        for source in value.sources:
            db.execute(
                "INSERT INTO sources VALUES(?,?)", (source.source_id, source.model_dump_json())
            )
        for span in value.evidence.spans:
            db.execute(
                "INSERT INTO spans VALUES(?,?,?)",
                (span.span_id, span.source_id, span.model_dump_json()),
            )
        db.execute(
            "INSERT INTO runs VALUES(?,?,?,?)",
            (LEGACY_RUN, "original-input-digest", "published", 1),
        )
        db.execute(
            "INSERT INTO tasks VALUES(?,?,?,?,?,?,?)",
            (
                LEGACY_TASK,
                LEGACY_RUN,
                "release_cataloging",
                "complete",
                0,
                "legacy-owner",
                value.catalog.model_dump_json(),
            ),
        )
        db.execute(
            "INSERT INTO versions VALUES(?,?,?,?,?)",
            (version_id, LEGACY_RUN, version_id, value.model_dump_json(), "published"),
        )
        db.execute(
            "INSERT INTO approvals VALUES(?,?,?,?)",
            (version_id, version_id, "Human teacher", 1000.0),
        )
        db.execute(
            "INSERT INTO releases VALUES(?,?,?,?)",
            (version_id, version_id, str(path.parent / "releases" / version_id), "available"),
        )
        db.execute(
            "INSERT INTO audit VALUES(?,?,?,?,?)",
            (1, "approved", version_id, "Human teacher", 1000.0),
        )
        db.commit()
        if schema_version == 2:
            db.executescript(LEGACY_V2_UPGRADE)
            db.commit()
    return value


def legacy_rows(path: Path) -> tuple[tuple[str, tuple[tuple[object, ...], ...]], ...]:
    with closing(sqlite3.connect(path)) as db:
        return tuple(
            (table, tuple(db.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()))
            for table in LEGACY_TABLES
        )


def database_dump(path: Path) -> str:
    with closing(sqlite3.connect(path)) as db:
        return "\n".join(db.iterdump())


@pytest.mark.parametrize("initial_version", [1, 2])
def test_populated_legacy_database_preserves_records_and_backfills_memberships(
    tmp_path: Path, initial_version: int
) -> None:
    path = tmp_path / "legacy.db"
    value = create_legacy_database(path, initial_version)
    before = legacy_rows(path)
    store = Workbench(path)
    assert legacy_rows(path) == before
    assert store.packet(value.digest()) == value
    assert store.source("fixture") == value.sources[0]
    assert store.spans() == value.evidence.spans
    assert store.cached(LEGACY_TASK, Catalog) == value.catalog
    assert store.usage(LEGACY_RUN).attempts == 1
    assert store.usage(LEGACY_RUN).measured_attempts == 0
    with store.connection() as db:
        assert tuple(db.execute("SELECT version FROM schema_version").fetchone()) == (3,)
        assert [tuple(row) for row in db.execute("SELECT * FROM release_versions")] == [
            (value.digest(), value.digest(), 1)
        ]
        assert [tuple(row) for row in db.execute("SELECT * FROM run_versions")] == [
            (LEGACY_RUN, value.digest())
        ]
        assert db.execute("SELECT COUNT(*) FROM run_leases").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM task_attempts").fetchone()[0] == 0
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        # Reusing an exact version in another release must no longer violate the v1 UNIQUE rule.
        db.execute(
            "INSERT INTO releases VALUES(?,?,?,?)",
            ("another-release", value.digest(), "/synthetic/second-release", "available"),
        )
        db.execute(
            "INSERT INTO release_versions VALUES(?,?,?)", ("another-release", value.digest(), 1)
        )


def test_reopening_an_upgraded_database_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    create_legacy_database(path)
    Workbench(path)
    before = database_dump(path)
    Workbench(path)
    assert database_dump(path) == before


def test_source_revocation_remains_effective_after_legacy_migration(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    value = create_legacy_database(path)
    store = Workbench(path)
    store.revoke("fixture", "Human teacher")
    assert store.source("fixture").status == "revoked"
    assert store.version_state(value.digest()) == "withdrawn"
    assert store.runs()[0].state == "withdrawn"
    with store.connection() as db:
        assert (
            db.execute("SELECT state FROM releases WHERE id=?", (value.digest(),)).fetchone()[0]
            == "withdrawn"
        )
        assert db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 1
        assert (
            db.execute("SELECT COUNT(*) FROM audit WHERE event='source_revoked'").fetchone()[0] == 1
        )
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("markers", [(), (99,), (1, 2)])
def test_unsupported_or_ambiguous_schema_is_rejected_without_mutation(
    tmp_path: Path, markers: tuple[int, ...]
) -> None:
    path = tmp_path / "unknown.db"
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE schema_version(version INTEGER PRIMARY KEY)")
        db.executemany("INSERT INTO schema_version VALUES(?)", ((marker,) for marker in markers))
        db.execute("CREATE TABLE preserved(value TEXT)")
        db.execute("INSERT INTO preserved VALUES('keep this')")
        db.commit()
    before = database_dump(path)
    with pytest.raises(StorageError, match="Unsupported workbench schema version"):
        Workbench(path)
    assert database_dump(path) == before


def test_unrelated_database_is_rejected_without_mutation(tmp_path: Path) -> None:
    path = tmp_path / "other-application.db"
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE learner_state(id INTEGER PRIMARY KEY,body TEXT)")
        db.execute("INSERT INTO learner_state VALUES(1,'unrelated learner state')")
        db.execute("PRAGMA user_version=42")
        db.commit()
    before = database_dump(path)
    with pytest.raises(StorageError, match="unrelated database"):
        Workbench(path)
    assert database_dump(path) == before
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 42


@pytest.mark.parametrize("conflicting_table", ["task_attempts", "run_versions"])
def test_failed_migration_rolls_back_schema_and_every_legacy_record(
    tmp_path: Path, conflicting_table: str
) -> None:
    path = tmp_path / "legacy.db"
    create_legacy_database(path)
    # Each collision fails after earlier ALTER/DROP/INSERT statements have already run.
    with closing(sqlite3.connect(path)) as db:
        db.execute(f'CREATE TABLE "{conflicting_table}"(sentinel TEXT)')
        db.execute(f'INSERT INTO "{conflicting_table}" VALUES(?)', ("preserve conflict evidence",))
        db.commit()
    before = database_dump(path)
    with pytest.raises(StorageError, match="database operation failed"):
        Workbench(path)
    assert database_dump(path) == before
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("SELECT version FROM schema_version").fetchone()[0] == 1
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='releases_v1'").fetchall()
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_stale_owner_cannot_clobber_the_successor_run_state(tmp_path: Path) -> None:
    store = Workbench(tmp_path / "workbench.db")
    run_id = store.start("state-ownership")
    previous = store.acquire_run(run_id)
    with store.connection() as db:
        db.execute("UPDATE run_leases SET lease_until=0 WHERE run_id=?", (run_id,))
    current = store.acquire_run(run_id)
    store.state(run_id, "awaiting_approval", current)
    store.state(run_id, "interrupted", previous)
    assert store.runs()[0].state == "awaiting_approval"
    store.release_run(run_id, previous)
    store.renew_run(run_id, current)


def test_stale_owner_cannot_save_or_replace_a_packet(tmp_path: Path) -> None:
    store = Workbench(tmp_path / "workbench.db")
    run_id = store.start("packet-ownership")
    previous = store.acquire_run(run_id)
    with store.connection() as db:
        db.execute("UPDATE run_leases SET lease_until=0 WHERE run_id=?", (run_id,))
    current = store.acquire_run(run_id)
    value = packet("owned")
    with pytest.raises(GateError, match="ownership expired or changed"):
        store.save_packet(run_id, value, previous)
    assert store.versions() == ()
    assert store.runs()[0].state == "running"
    version = store.save_packet(run_id, value, current)
    assert store.packet(version) == value
    assert store.runs()[0].state == "awaiting_approval"
