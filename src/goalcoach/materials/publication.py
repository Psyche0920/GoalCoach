"""Human-gated, dependency-complete exports compatible with GoalCoach content."""

from __future__ import annotations

import hashlib
import heapq
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Literal

from pydantic import Field

from goalcoach.materials.models import (
    Card,
    Catalog,
    Exercise,
    GateError,
    Identifier,
    Packet,
    Record,
    Review,
    Source,
    StorageError,
)
from goalcoach.materials.store import Workbench
from goalcoach.materials.workflow import validate_evidence, validate_material

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ArtifactName = Literal["materials.db", "materials.md", "materials.jsonl", "review-report.json"]
ARTIFACT_NAMES = frozenset(
    {"materials.db", "materials.md", "materials.jsonl", "review-report.json"}
)

CONTENT_SCHEMA = """
CREATE TABLE curriculum_concepts(concept_id TEXT PRIMARY KEY,hsk_level INTEGER,sequence_no INTEGER UNIQUE,slug TEXT UNIQUE,title_zh TEXT,title_en TEXT,concept_type TEXT,communicative_goal TEXT,grammar_focus TEXT,vocabulary_focus TEXT,difficulty INTEGER,estimated_minutes INTEGER,source_ref TEXT,is_active INTEGER,metadata TEXT);
CREATE TABLE teaching_cards(card_id INTEGER PRIMARY KEY,concept_id TEXT REFERENCES curriculum_concepts(concept_id),card_order INTEGER,card_type TEXT,prompt_zh TEXT,pinyin TEXT,meaning_en TEXT,explanation_en TEXT,example_zh TEXT,example_pinyin TEXT,example_en TEXT,payload TEXT,UNIQUE(concept_id,card_order));
CREATE TABLE exercises(exercise_id TEXT PRIMARY KEY,concept_id TEXT REFERENCES curriculum_concepts(concept_id),exercise_order INTEGER,exercise_type TEXT,prompt TEXT,prompt_pinyin TEXT,instruction TEXT,answer TEXT,options TEXT,accepted_answers TEXT,explanation TEXT,target_tokens TEXT,error_tags TEXT,difficulty INTEGER,points INTEGER,metadata TEXT,UNIQUE(concept_id,exercise_order));
CREATE TABLE concept_prerequisites(concept_id TEXT REFERENCES curriculum_concepts(concept_id),prerequisite_id TEXT REFERENCES curriculum_concepts(concept_id),PRIMARY KEY(concept_id,prerequisite_id),CHECK(concept_id<>prerequisite_id));
CREATE TABLE published_provenance(item_id TEXT,claim_id TEXT,source_id TEXT,locator TEXT,source_title TEXT,rights_evidence TEXT);
CREATE TABLE release_manifest(release_id TEXT PRIMARY KEY,content_hash TEXT,schema_version INTEGER);
CREATE TABLE release_units(version_id TEXT PRIMARY KEY,concept_id TEXT UNIQUE REFERENCES curriculum_concepts(concept_id),sequence_no INTEGER UNIQUE);
"""


class ReleaseUnit(Record):
    """An exact approved version and its position in a dependency-complete release."""

    version_id: Digest
    concept_id: Identifier
    sequence_no: int = Field(ge=1)
    prerequisite_ids: tuple[Identifier, ...]


class ReleaseManifest(Record):
    release_id: Digest
    schema_version: Literal[2] = 2
    units: tuple[ReleaseUnit, ...] = Field(min_length=1)
    files: dict[ArtifactName, Digest]


class LegacyReleaseManifest(Record):
    """Read existing singleton releases without rewriting their immutable files."""

    release_id: Digest
    schema_version: Literal[1]
    files: dict[ArtifactName, Digest]


class UnitReviewReport(Record):
    version_id: Digest
    concept_id: Identifier
    knowledge: Review
    teaching: Review
    catalog: Catalog


class BatchReviewReport(Record):
    release_id: Digest
    units: tuple[UnitReviewReport, ...]


class ReleaseIdentity(Record):
    schema_version: Literal[2] = 2
    units: tuple[ReleaseUnit, ...]

    @property
    def release_id(self) -> str:
        # Keep existing single-unit identifiers stable across the migration.
        return self.units[0].version_id if len(self.units) == 1 else self.digest()


def _card_id(concept_id: str, item_id: str) -> int:
    return int(hashlib.sha256(f"{concept_id}:{item_id}".encode()).hexdigest()[:15], 16)


class PublicationService:
    def __init__(self, store: Workbench) -> None:
        self.store = store

    def export(self, version_id: str, root: Path) -> Path:
        """Publish a self-contained singleton using the same batch gates."""
        return self.export_many((version_id,), root)

    def export_many(self, version_ids: tuple[str, ...], root: Path) -> Path:
        """Publish all selected exact versions atomically in prerequisite order."""
        if not version_ids or len(version_ids) != len(set(version_ids)):
            raise GateError("A release requires a nonempty selection of distinct version IDs.")
        packets = self._order_packets(tuple(self.store.packet(version) for version in version_ids))
        if {packet.digest() for packet in packets} != set(version_ids):
            raise GateError("Stored material does not match its immutable version ID.")
        units = tuple(
            ReleaseUnit(
                version_id=packet.digest(),
                concept_id=packet.brief.concept_id,
                sequence_no=sequence,
                prerequisite_ids=tuple(sorted(packet.brief.prerequisite_ids)),
            )
            for sequence, packet in enumerate(packets, 1)
        )
        identity = ReleaseIdentity(units=units)
        release_id = identity.release_id
        root = root.resolve()
        target = root / release_id
        try:
            root.mkdir(parents=True, exist_ok=True)
            with self.store.connection() as db:
                # Source revocation and the complete release registration share this lock.
                db.execute("BEGIN IMMEDIATE")
                for packet in packets:
                    self._require_current_approval(db, packet)
                existing = db.execute(
                    "SELECT path,state FROM releases WHERE id=?", (release_id,)
                ).fetchone()
                if existing:
                    if existing[1] != "available":
                        raise GateError("Release was withdrawn.")
                    saved = Path(existing[0])
                    manifest = self._verified_manifest(saved)
                    if manifest.release_id != release_id:
                        raise GateError("Registered release identity does not match its manifest.")
                    if isinstance(manifest, ReleaseManifest) and manifest.units != units:
                        raise GateError(
                            "Registered release members do not match the selected versions."
                        )
                    return saved
                if target.exists():
                    raise GateError(
                        "An unregistered release directory exists; inspect it before retrying."
                    )
                with TemporaryDirectory(prefix=".building-", dir=root) as temporary:
                    staging = Path(temporary)
                    self._build(packets, identity, staging)
                    self.verify(staging)
                    os.replace(staging, target)
                db.execute(
                    "INSERT INTO releases(id,version_id,path,state) VALUES(?,?,?,'available')",
                    (release_id, units[0].version_id, str(target)),
                )
                db.executemany(
                    "INSERT INTO release_versions(release_id,version_id,sequence_no) VALUES(?,?,?)",
                    ((release_id, unit.version_id, unit.sequence_no) for unit in units),
                )
                for unit in units:
                    db.execute(
                        "UPDATE versions SET state='published' WHERE id=?", (unit.version_id,)
                    )
                    db.execute(
                        "UPDATE runs SET state='published' WHERE id IN (SELECT run_id FROM run_versions WHERE version_id=?)",
                        (unit.version_id,),
                    )
            return target
        except (OSError, sqlite3.Error) as exc:
            raise StorageError(
                "Release build failed; unregistered staging artifacts are not published."
            ) from exc

    @staticmethod
    def _order_packets(packets: tuple[Packet, ...]) -> tuple[Packet, ...]:
        concepts = {packet.brief.concept_id: packet for packet in packets}
        if len(concepts) != len(packets):
            raise GateError("A release cannot contain duplicate concept IDs.")
        item_ids: set[str] = set()
        card_ids: set[int] = set()
        for packet in packets:
            validate_evidence(packet.claims, packet.evidence, packet.sources)
            validate_material(packet.material, packet.claims)
            if not packet.quality_passes:
                raise GateError(
                    "Publication requires passing independent reviews and combined quality gates."
                )
            items: tuple[Card | Exercise, ...] = (
                *packet.material.cards,
                *packet.material.exercises,
            )
            for item in items:
                item_id = item.item_id if isinstance(item, Card) else item.exercise_id
                if item_id in item_ids:
                    raise GateError("A release cannot contain duplicate card or exercise IDs.")
                item_ids.add(item_id)
                if isinstance(item, Card):
                    card_id = _card_id(packet.brief.concept_id, item.item_id)
                    if card_id in card_ids:
                        raise GateError("Generated integer card IDs collide.")
                    card_ids.add(card_id)
            prerequisites = packet.brief.prerequisite_ids
            if len(set(prerequisites)) != len(prerequisites):
                raise GateError("A concept cannot repeat prerequisite IDs.")
            missing = set(prerequisites) - concepts.keys()
            if missing:
                raise GateError(
                    "A release must be self-contained; include every prerequisite concept: "
                    + ", ".join(sorted(missing))
                )
        remaining = {
            concept_id: set(packet.brief.prerequisite_ids)
            for concept_id, packet in concepts.items()
        }
        dependents: dict[str, set[str]] = {concept_id: set() for concept_id in concepts}
        for concept_id, pending_prerequisites in remaining.items():
            for prerequisite in pending_prerequisites:
                dependents[prerequisite].add(concept_id)
        ready = [concept_id for concept_id, prerequisites in remaining.items() if not prerequisites]
        heapq.heapify(ready)
        ordered: list[Packet] = []
        while ready:
            concept_id = heapq.heappop(ready)
            ordered.append(concepts[concept_id])
            for dependent in sorted(dependents[concept_id]):
                remaining[dependent].remove(concept_id)
                if not remaining[dependent]:
                    heapq.heappush(ready, dependent)
        if len(ordered) != len(packets):
            raise GateError("Prerequisite cycles prevent publication.")
        return tuple(ordered)

    @staticmethod
    def _require_current_approval(db: sqlite3.Connection, packet: Packet) -> None:
        version_id = packet.digest()
        approval = db.execute(
            "SELECT a.digest,v.state,v.digest,v.body FROM approvals a JOIN versions v ON v.id=a.version_id WHERE v.id=?",
            (version_id,),
        ).fetchone()
        if (
            approval is None
            or approval[0] != version_id
            or approval[1] not in {"approved", "published"}
            or approval[2] != version_id
            or Packet.model_validate_json(approval[3]).digest() != version_id
        ):
            raise GateError("Publication requires human approval of this exact version.")
        for original in packet.sources:
            row = db.execute(
                "SELECT body FROM sources WHERE id=?", (original.source_id,)
            ).fetchone()
            if row is None:
                raise GateError("Source missing at publication.")
            source = Source.model_validate_json(row[0])
            source.require("analysis")
            source.require("redistribution")
            source.require("adaptation")
            if source != original:
                raise GateError("Source attribution or permissions changed after material review.")

    def _build(self, packets: tuple[Packet, ...], identity: ReleaseIdentity, folder: Path) -> None:
        with closing(sqlite3.connect(folder / "materials.db")) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(CONTENT_SCHEMA)
            for unit, packet in zip(identity.units, packets, strict=True):
                self._write_unit(db, unit, packet)
            for unit in identity.units:
                db.executemany(
                    "INSERT INTO concept_prerequisites VALUES(?,?)",
                    ((unit.concept_id, prerequisite) for prerequisite in unit.prerequisite_ids),
                )
            db.execute(
                "INSERT INTO release_manifest VALUES(?,?,2)",
                (identity.release_id, identity.release_id),
            )
            if db.execute("PRAGMA foreign_key_check").fetchall():
                raise GateError("Release contains broken foreign keys.")
            db.commit()
        # JSONL lines follow manifest order and contain only approved material.
        (folder / "materials.jsonl").write_text(
            "".join(packet.material.model_dump_json() + "\n" for packet in packets),
            encoding="utf-8",
        )
        (folder / "materials.md").write_text(
            "\n---\n\n".join(self._markdown(packet) for packet in packets), encoding="utf-8"
        )
        report = BatchReviewReport(
            release_id=identity.release_id,
            units=tuple(
                UnitReviewReport(
                    version_id=packet.digest(),
                    concept_id=packet.brief.concept_id,
                    knowledge=packet.knowledge_review,
                    teaching=packet.teaching_review,
                    catalog=packet.catalog,
                )
                for packet in packets
            ),
        )
        (folder / "review-report.json").write_text(
            report.model_dump_json(indent=2), encoding="utf-8"
        )
        artifacts: tuple[ArtifactName, ...] = (
            "materials.db",
            "materials.md",
            "materials.jsonl",
            "review-report.json",
        )
        manifest = ReleaseManifest(
            release_id=identity.release_id,
            units=identity.units,
            files={
                name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in artifacts
            },
        )
        (folder / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def _write_unit(db: sqlite3.Connection, unit: ReleaseUnit, packet: Packet) -> None:
        brief, material = packet.brief, packet.material
        db.execute(
            "INSERT INTO curriculum_concepts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                brief.concept_id,
                brief.hsk_level,
                unit.sequence_no,
                brief.concept_id,
                material.title_zh,
                material.title_en,
                "mixed",
                brief.objective,
                json.dumps(packet.blueprint.grammar),
                json.dumps(packet.blueprint.vocabulary),
                brief.hsk_level,
                material.estimated_minutes,
                brief.framework,
                1,
                "{}",
            ),
        )
        db.execute(
            "INSERT INTO release_units VALUES(?,?,?)",
            (unit.version_id, unit.concept_id, unit.sequence_no),
        )
        for order, card in enumerate(material.cards, 1):
            db.execute(
                "INSERT INTO teaching_cards VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    _card_id(brief.concept_id, card.item_id),
                    brief.concept_id,
                    order,
                    card.card_type,
                    card.text_zh,
                    card.pinyin,
                    card.meaning_en,
                    card.explanation_en,
                    card.text_zh,
                    card.pinyin,
                    card.meaning_en,
                    json.dumps({"item_id": card.item_id}),
                ),
            )
        for order, exercise in enumerate(material.exercises, 1):
            db.execute(
                "INSERT INTO exercises VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    exercise.exercise_id,
                    brief.concept_id,
                    order,
                    exercise.exercise_type,
                    exercise.prompt,
                    None,
                    exercise.instruction,
                    json.dumps({"value": exercise.answer}),
                    json.dumps(exercise.options),
                    json.dumps(exercise.accepted_answers),
                    exercise.explanation,
                    "[]",
                    json.dumps(exercise.error_tags),
                    brief.hsk_level,
                    10,
                    "{}",
                ),
            )
        sources = {source.source_id: source for source in packet.sources}
        spans = {span.span_id: span for span in packet.evidence.spans}
        claims = {claim.claim_id: claim for claim in packet.claims.claims}
        items: tuple[Card | Exercise, ...] = (*material.cards, *material.exercises)
        for item in items:
            item_id = item.item_id if isinstance(item, Card) else item.exercise_id
            for claim_id in item.claim_ids:
                for span_id in claims[claim_id].span_ids:
                    span = spans[span_id]
                    source = sources[span.source_id]
                    db.execute(
                        "INSERT INTO published_provenance VALUES(?,?,?,?,?,?)",
                        (
                            item_id,
                            claim_id,
                            source.source_id,
                            span.locator,
                            source.title,
                            source.rights_evidence,
                        ),
                    )

    @staticmethod
    def _markdown(packet: Packet) -> str:
        brief, material = packet.brief, packet.material
        lines = [
            f"# {material.title_en}",
            "",
            material.title_zh,
            "",
            f"Concept: {brief.concept_id}",
            "",
            f"Version: {packet.digest()}",
            "",
            f"Objective: {brief.objective}",
            "",
            f"Prerequisites: {', '.join(sorted(brief.prerequisite_ids)) or 'None'}",
            "",
        ]
        for card in material.cards:
            lines.extend(
                [
                    f"## {card.card_type.title()}",
                    "",
                    card.text_zh,
                    "",
                    card.pinyin,
                    "",
                    card.meaning_en,
                    "",
                    card.explanation_en,
                    "",
                ]
            )
        lines.extend(["## Exercises", ""])
        for exercise in material.exercises:
            lines.extend(
                [
                    exercise.prompt,
                    "",
                    exercise.instruction,
                    "",
                    *[f"- {option}" for option in exercise.options],
                    "",
                    f"Answer: {exercise.answer}",
                    "",
                    exercise.explanation,
                    "",
                ]
            )
        lines.extend(["## Teacher notes", "", material.teacher_notes, "", "## Sources", ""])
        for source in packet.sources:
            lines.append(
                f"- {source.title} — {source.publisher}; {source.edition}; {source.url}; rights: {source.rights_evidence}"
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def verify(folder: Path) -> None:
        """Check immutable files and manifest membership; availability remains a registry gate."""
        PublicationService._verified_manifest(folder)

    @staticmethod
    def _verified_manifest(folder: Path) -> ReleaseManifest | LegacyReleaseManifest:
        try:
            raw = (folder / "manifest.json").read_text(encoding="utf-8")
            manifest: ReleaseManifest | LegacyReleaseManifest
            try:
                manifest = ReleaseManifest.model_validate_json(raw)
            except ValueError:
                manifest = LegacyReleaseManifest.model_validate_json(raw)
            if set(manifest.files) != ARTIFACT_NAMES:
                raise GateError("Unexpected release manifest entries.")
            for name, digest in manifest.files.items():
                artifact = folder / name
                if artifact.is_symlink() or not artifact.is_file():
                    raise GateError("Release artifacts must be regular files.")
                if hashlib.sha256(artifact.read_bytes()).hexdigest() != digest:
                    raise GateError("Release integrity check failed.")
            with closing(
                sqlite3.connect((folder / "materials.db").resolve().as_uri() + "?mode=ro", uri=True)
            ) as db:
                stored_identity = db.execute(
                    "SELECT release_id,content_hash,schema_version FROM release_manifest"
                ).fetchall()
                if stored_identity != [
                    (manifest.release_id, manifest.release_id, manifest.schema_version)
                ]:
                    raise GateError("Database release identity differs from the manifest.")
            if isinstance(manifest, ReleaseManifest):
                identity = ReleaseIdentity(units=manifest.units)
                if identity.release_id != manifest.release_id:
                    raise GateError("Release identity does not match its exact unit versions.")
                if tuple(unit.sequence_no for unit in manifest.units) != tuple(
                    range(1, len(manifest.units) + 1)
                ):
                    raise GateError("Release unit order is not contiguous.")
                seen_concepts: set[str] = set()
                seen_versions: set[str] = set()
                for unit in manifest.units:
                    if unit.concept_id in seen_concepts or unit.version_id in seen_versions:
                        raise GateError("Release manifest contains duplicate units.")
                    if not set(unit.prerequisite_ids) <= seen_concepts:
                        raise GateError("Release manifest is not dependency-complete and ordered.")
                    seen_concepts.add(unit.concept_id)
                    seen_versions.add(unit.version_id)
                with closing(
                    sqlite3.connect(
                        (folder / "materials.db").resolve().as_uri() + "?mode=ro", uri=True
                    )
                ) as db:
                    stored_units = db.execute(
                        "SELECT version_id,concept_id,sequence_no FROM release_units ORDER BY sequence_no"
                    ).fetchall()
                    expected_units = [
                        (unit.version_id, unit.concept_id, unit.sequence_no)
                        for unit in manifest.units
                    ]
                    if stored_units != expected_units:
                        raise GateError("Database release members differ from the manifest.")
                    stored_prerequisites = db.execute(
                        "SELECT concept_id,prerequisite_id FROM concept_prerequisites ORDER BY concept_id,prerequisite_id"
                    ).fetchall()
                    expected_prerequisites = sorted(
                        (unit.concept_id, prerequisite)
                        for unit in manifest.units
                        for prerequisite in unit.prerequisite_ids
                    )
                    if (
                        stored_prerequisites != expected_prerequisites
                        or db.execute("PRAGMA foreign_key_check").fetchall()
                    ):
                        raise GateError("Database prerequisites differ from the release manifest.")
            return manifest
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            raise StorageError("Cannot verify release manifest.") from exc
