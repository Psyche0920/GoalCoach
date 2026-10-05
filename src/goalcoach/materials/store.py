"""SQLite persistence with atomic task leases and immutable artifacts."""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from goalcoach.materials.models import (
    GateError,
    Packet,
    Record,
    RunSummary,
    Source,
    Span,
    StorageError,
    TaskSummary,
    UsageRecord,
    UsageSummary,
    VersionSummary,
)

T = TypeVar("T", bound=Record)

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY CHECK(version=1));
INSERT OR IGNORE INTO schema_version VALUES(1);
CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS spans(id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id), body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, input_hash TEXT NOT NULL, state TEXT NOT NULL, calls INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS tasks(key TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), role TEXT NOT NULL, state TEXT NOT NULL, lease_until REAL NOT NULL, owner TEXT NOT NULL, body TEXT);
CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), digest TEXT NOT NULL UNIQUE, body TEXT NOT NULL, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS approvals(version_id TEXT PRIMARY KEY REFERENCES versions(id), digest TEXT NOT NULL, reviewer TEXT NOT NULL, approved_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS releases(id TEXT PRIMARY KEY, version_id TEXT NOT NULL UNIQUE REFERENCES versions(id), path TEXT NOT NULL, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, event TEXT NOT NULL, subject TEXT NOT NULL, actor TEXT NOT NULL, created_at REAL NOT NULL);
"""


class Workbench:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.connection() as db:
                self._initialize(db)
        except OSError as exc:
            raise StorageError("Cannot initialize workbench directory.") from exc

    @staticmethod
    def _initialize(db: sqlite3.Connection) -> None:
        """Upgrade the original workbench atomically without losing approvals or history."""
        db.execute("BEGIN IMMEDIATE")
        exists = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchone()
        if exists is None:
            other_tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            if other_tables:
                raise StorageError("Refusing to initialize an unrelated database.")
            for statement in SCHEMA.split(";"):
                if statement.strip():
                    db.execute(statement)
        versions = db.execute("SELECT version FROM schema_version").fetchall()
        if len(versions) != 1 or versions[0][0] not in {1, 2, 3}:
            raise StorageError("Unsupported workbench schema version.")
        if versions[0][0] == 1:
            db.execute("ALTER TABLE releases RENAME TO releases_v1")
            db.execute(
                "CREATE TABLE releases(id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES versions(id), path TEXT NOT NULL, state TEXT NOT NULL)"
            )
            db.execute("INSERT INTO releases SELECT * FROM releases_v1")
            db.execute("DROP TABLE releases_v1")
            db.execute(
                "CREATE TABLE release_versions(release_id TEXT NOT NULL REFERENCES releases(id), version_id TEXT NOT NULL REFERENCES versions(id), sequence_no INTEGER NOT NULL CHECK(sequence_no>0), PRIMARY KEY(release_id,version_id), UNIQUE(release_id,sequence_no))"
            )
            db.execute("INSERT INTO release_versions SELECT id,version_id,1 FROM releases")
            db.execute(
                "CREATE TABLE task_attempts(owner TEXT PRIMARY KEY, task_key TEXT NOT NULL REFERENCES tasks(key), run_id TEXT NOT NULL REFERENCES runs(id), outcome TEXT NOT NULL, usage_json TEXT, started_at REAL NOT NULL)"
            )
            db.execute("DROP TABLE schema_version")
            db.execute("CREATE TABLE schema_version(version INTEGER PRIMARY KEY CHECK(version=2))")
            db.execute("INSERT INTO schema_version VALUES(2)")
        if versions[0][0] in {1, 2}:
            db.execute(
                "CREATE TABLE run_leases(run_id TEXT PRIMARY KEY REFERENCES runs(id), owner TEXT NOT NULL, lease_until REAL NOT NULL)"
            )
            db.execute(
                "CREATE TABLE run_versions(run_id TEXT NOT NULL REFERENCES runs(id), version_id TEXT NOT NULL REFERENCES versions(id), PRIMARY KEY(run_id,version_id))"
            )
            db.execute("INSERT INTO run_versions SELECT run_id,id FROM versions")
            db.execute("DROP TABLE schema_version")
            db.execute("CREATE TABLE schema_version(version INTEGER PRIMARY KEY CHECK(version=3))")
            db.execute("INSERT INTO schema_version VALUES(3)")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db: sqlite3.Connection | None = None
        try:
            db = sqlite3.connect(self.path, timeout=10)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            with db:
                yield db
        except sqlite3.Error as exc:
            raise StorageError("Workbench database operation failed.") from exc
        finally:
            if db is not None:
                db.close()

    def register(self, source: Source) -> None:
        source.require("analysis")
        with self.connection() as db:
            row = db.execute("SELECT body FROM sources WHERE id=?", (source.source_id,)).fetchone()
            if row is not None and str(row[0]) != source.model_dump_json():
                raise GateError("Source IDs are immutable; register a new source version.")
            db.execute(
                "INSERT OR IGNORE INTO sources VALUES(?,?)",
                (source.source_id, source.model_dump_json()),
            )

    def sources(self) -> tuple[Source, ...]:
        with self.connection() as db:
            return tuple(
                Source.model_validate_json(row[0])
                for row in db.execute("SELECT body FROM sources ORDER BY id")
            )

    def source(self, source_id: str) -> Source:
        for source in self.sources():
            if source.source_id == source_id:
                return source
        raise GateError("Unknown source ID.")

    def save_spans(self, spans: tuple[Span, ...]) -> None:
        with self.connection() as db:
            for span in spans:
                db.execute(
                    "INSERT OR IGNORE INTO spans VALUES(?,?,?)",
                    (span.span_id, span.source_id, span.model_dump_json()),
                )

    def spans(self) -> tuple[Span, ...]:
        with self.connection() as db:
            return tuple(
                Span.model_validate_json(row[0])
                for row in db.execute("SELECT body FROM spans ORDER BY id")
            )

    def start(self, input_hash: str, run_id: str | None = None) -> str:
        run_id = run_id or uuid4().hex
        with self.connection() as db:
            row = db.execute("SELECT input_hash FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is not None and row[0] != input_hash:
                raise GateError("Resume inputs differ from the original run.")
            db.execute(
                "INSERT OR IGNORE INTO runs(id,input_hash,state) VALUES(?,?,'running')",
                (run_id, input_hash),
            )
        return run_id

    def state(self, run_id: str, state: str, owner: str | None = None) -> None:
        with self.connection() as db:
            if owner is None:
                db.execute("UPDATE runs SET state=? WHERE id=?", (state, run_id))
            else:
                db.execute(
                    "UPDATE runs SET state=? WHERE id=? AND EXISTS(SELECT 1 FROM run_leases WHERE run_id=? AND owner=? AND lease_until>?)",
                    (state, run_id, run_id, owner, time.time()),
                )

    def acquire_run(self, run_id: str) -> str:
        owner = uuid4().hex
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT lease_until FROM run_leases WHERE run_id=?", (run_id,)
            ).fetchone()
            if row is not None and row[0] > time.time():
                raise GateError(
                    "Run is leased by another worker; resume after it finishes or its lease expires."
                )
            db.execute(
                "INSERT INTO run_leases VALUES(?,?,?) ON CONFLICT(run_id) DO UPDATE SET owner=excluded.owner,lease_until=excluded.lease_until",
                (run_id, owner, time.time() + 180),
            )
        return owner

    def renew_run(self, run_id: str, owner: str) -> None:
        with self.connection() as db:
            changed = db.execute(
                "UPDATE run_leases SET lease_until=? WHERE run_id=? AND owner=? AND lease_until>?",
                (time.time() + 180, run_id, owner, time.time()),
            ).rowcount
            if changed != 1:
                raise GateError("Run lease ownership expired or changed.")

    def release_run(self, run_id: str, owner: str) -> None:
        with self.connection() as db:
            db.execute("DELETE FROM run_leases WHERE run_id=? AND owner=?", (run_id, owner))

    def cached(self, key: str, model: type[T]) -> T | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT body FROM tasks WHERE key=? AND state='complete'", (key,)
            ).fetchone()
        return None if row is None else model.model_validate_json(row[0])

    def claim_task(self, key: str, run_id: str, role: str, limit: int) -> str:
        owner = uuid4().hex
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state,lease_until FROM tasks WHERE key=?", (key,)).fetchone()
            if row is not None and (row[0] == "complete" or row[1] > time.time()):
                raise GateError(
                    "Task is already complete or leased by another worker; resume later."
                )
            changed = db.execute(
                "UPDATE runs SET calls=calls+1 WHERE id=? AND calls<?", (run_id, limit)
            ).rowcount
            if changed != 1:
                raise GateError("Run request budget exhausted.")
            db.execute(
                "INSERT INTO tasks VALUES(?,?,?,'running',?,?,NULL) ON CONFLICT(key) DO UPDATE SET state='running',lease_until=excluded.lease_until,owner=excluded.owner",
                (key, run_id, role, time.time() + 180, owner),
            )
            db.execute(
                "INSERT INTO task_attempts VALUES(?,?,?,'running',NULL,?)",
                (owner, key, run_id, time.time()),
            )
        return owner

    def finish_task(
        self, key: str, owner: str, result: Record | None, usage: UsageRecord | None = None
    ) -> None:
        with self.connection() as db:
            changed = db.execute(
                "UPDATE tasks SET state=?,lease_until=0,body=? WHERE key=? AND owner=?",
                (
                    "complete" if result else "failed",
                    result.model_dump_json() if result else None,
                    key,
                    owner,
                ),
            ).rowcount
            if changed != 1:
                raise GateError("Task lease ownership changed.")
            db.execute(
                "UPDATE task_attempts SET outcome=?,usage_json=? WHERE owner=?",
                (
                    "complete" if result else "failed",
                    usage.model_dump_json() if usage else None,
                    owner,
                ),
            )

    def save_packet(self, run_id: str, packet: Packet, owner: str | None = None) -> str:
        version_id = packet.digest()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if owner is not None:
                lease = db.execute(
                    "SELECT 1 FROM run_leases WHERE run_id=? AND owner=? AND lease_until>?",
                    (run_id, owner, time.time()),
                ).fetchone()
                if lease is None:
                    raise GateError(
                        "Run lease ownership expired or changed before saving the packet."
                    )
            db.execute(
                "INSERT OR IGNORE INTO versions VALUES(?,?,?,?, 'awaiting_approval')",
                (version_id, run_id, packet.digest(), packet.model_dump_json()),
            )
            db.execute("INSERT OR IGNORE INTO run_versions VALUES(?,?)", (run_id, version_id))
            db.execute(
                "UPDATE runs SET state=(SELECT state FROM versions WHERE id=?) WHERE id=?",
                (version_id, run_id),
            )
        return version_id

    def version_state(self, version_id: str) -> str:
        with self.connection() as db:
            row = db.execute("SELECT state FROM versions WHERE id=?", (version_id,)).fetchone()
        if row is None:
            raise GateError("Unknown material version.")
        return str(row[0])

    def packet(self, version_id: str) -> Packet:
        with self.connection() as db:
            row = db.execute("SELECT body FROM versions WHERE id=?", (version_id,)).fetchone()
        if row is None:
            raise GateError("Unknown material version.")
        return Packet.model_validate_json(row[0])

    def approve(self, version_id: str, expected_hash: str, reviewer: str) -> None:
        if not reviewer.strip():
            raise GateError("An identified human reviewer is required.")
        packet = self.packet(version_id)
        if packet.digest() != expected_hash:
            raise GateError("Approval hash does not match the reviewed version.")
        if not packet.quality_passes:
            raise GateError("Both independent reviews must pass.")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            for source in packet.sources:
                row = db.execute(
                    "SELECT body FROM sources WHERE id=?", (source.source_id,)
                ).fetchone()
                if row is None:
                    raise GateError("Source is missing at approval.")
                current = Source.model_validate_json(row[0])
                current.require("redistribution")
                current.require("adaptation")
            changed = db.execute(
                "UPDATE versions SET state='approved' WHERE id=? AND state='awaiting_approval'",
                (version_id,),
            ).rowcount
            if changed != 1:
                raise GateError("Only a version awaiting approval can be approved.")
            db.execute(
                "INSERT INTO approvals VALUES(?,?,?,?)",
                (version_id, expected_hash, reviewer, time.time()),
            )
            db.execute(
                "INSERT INTO audit(event,subject,actor,created_at) VALUES('approved',?,?,?)",
                (version_id, reviewer, time.time()),
            )

    def revoke(self, source_id: str, actor: str) -> None:
        if not actor.strip():
            raise GateError("An identified reviewer is required.")
        source = self.source(source_id).model_copy(update={"status": "revoked"})
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE sources SET body=? WHERE id=?", (source.model_dump_json(), source_id)
            )
            for row in db.execute("SELECT id,body FROM versions").fetchall():
                packet = Packet.model_validate_json(row[1])
                if source_id in {s.source_id for s in packet.sources}:
                    db.execute("UPDATE versions SET state='withdrawn' WHERE id=?", (row[0],))
                    db.execute(
                        "UPDATE runs SET state='withdrawn' WHERE id IN (SELECT run_id FROM run_versions WHERE version_id=?)",
                        (row[0],),
                    )
                    db.execute(
                        "UPDATE releases SET state='withdrawn' WHERE id IN (SELECT release_id FROM release_versions WHERE version_id=?)",
                        (row[0],),
                    )
            db.execute(
                "INSERT INTO audit(event,subject,actor,created_at) VALUES('source_revoked',?,?,?)",
                (source_id, actor, time.time()),
            )

    def runs(self) -> tuple[RunSummary, ...]:
        with self.connection() as db:
            return tuple(
                RunSummary(run_id=r[0], state=r[1], request_count=r[2])
                for r in db.execute("SELECT id,state,calls FROM runs ORDER BY rowid DESC")
            )

    def versions(self) -> tuple[VersionSummary, ...]:
        with self.connection() as db:
            return tuple(
                VersionSummary(version_id=r[0], run_id=r[1], state=r[2])
                for r in db.execute("SELECT id,run_id,state FROM versions ORDER BY rowid DESC")
            )

    def tasks(self, run_id: str) -> tuple[TaskSummary, ...]:
        with self.connection() as db:
            return tuple(
                TaskSummary(task_id=r[0], role=r[1], state=r[2], result_json=r[3])
                for r in db.execute(
                    "SELECT key,role,state,body FROM tasks WHERE run_id=? ORDER BY rowid", (run_id,)
                )
            )

    def usage(self, run_id: str | None = None) -> UsageSummary:
        with self.connection() as db:
            rows = db.execute(
                "SELECT usage_json FROM task_attempts WHERE (? IS NULL OR run_id=?)",
                (run_id, run_id),
            ).fetchall()
            attempt_row = db.execute(
                "SELECT COALESCE(SUM(calls),0) FROM runs WHERE (? IS NULL OR id=?)",
                (run_id, run_id),
            ).fetchone()
            attempts = int(attempt_row[0])
        measured = tuple(
            UsageRecord.model_validate_json(row[0]) for row in rows if row[0] is not None
        )
        priced = tuple(u.estimated_cost_usd for u in measured if u.estimated_cost_usd is not None)
        return UsageSummary(
            attempts=attempts,
            measured_attempts=len(measured),
            priced_attempts=len(priced),
            input_tokens=sum(u.input_tokens for u in measured),
            output_tokens=sum(u.output_tokens for u in measured),
            known_estimated_cost_usd=sum(priced, Decimal(0)),
        )

    def status(self) -> str:
        with self.connection() as db:
            lines = [
                f"run {r[0]} state={r[1]} requests={r[2]}"
                for r in db.execute("SELECT id,state,calls FROM runs")
            ]
            lines += [
                f"version {r[0]} state={r[1]}" for r in db.execute("SELECT id,state FROM versions")
            ]
            lines += [
                f"release {r[0]} state={r[1]} path={r[2]}"
                for r in db.execute("SELECT id,state,path FROM releases")
            ]
        return "\n".join(lines) or "No production runs yet."
