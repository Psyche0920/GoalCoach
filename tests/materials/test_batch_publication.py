"""Batch release gates, atomic registration, and GoalCoach dependency round trips."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from goalcoach.infrastructure.persistence.repositories import ContentRepository
from goalcoach.materials.models import (
    Blueprint,
    Brief,
    Card,
    Catalog,
    Claim,
    Claims,
    Evidence,
    Exercise,
    GateError,
    Material,
    Packet,
    Review,
    Source,
    Span,
    StorageError,
)
from goalcoach.materials.publication import PublicationService, ReleaseManifest
from goalcoach.materials.store import Workbench


def packet(
    concept_id: str, prerequisites: tuple[str, ...] = (), source_id: str = "fixture"
) -> Packet:
    """Use original synthetic content so validation never needs a remote model."""
    source = Source(
        source_id=source_id,
        title="Original synthetic teaching source",
        category="textbook",
        publisher="Test author",
        edition="1",
        rights_evidence="Original test fixture, approved by its author",
        allowed_uses=("analysis", "adaptation", "redistribution"),
        approved_by="test-author",
    )
    review = Review(
        verdict="pass",
        accuracy=5,
        teachability=5,
        evidence=5,
        difficulty=5,
        naturalness=5,
        issues=(),
        rationale="All test gates pass.",
    )
    return Packet(
        brief=Brief(
            concept_id=concept_id,
            objective="Greet someone",
            framework="Test curriculum",
            hsk_level=1,
            prerequisite_ids=prerequisites,
        ),
        sources=(source,),
        evidence=Evidence(
            spans=(
                Span(
                    span_id=f"{source_id}-span",
                    source_id=source_id,
                    locator="page 1",
                    text="RAW SOURCE SENTINEL: 你好 means hello.",
                    source_hash="fixture-hash",
                ),
            )
        ),
        claims=Claims(
            claims=(
                Claim(
                    claim_id="greeting",
                    statement="你好 means hello.",
                    span_ids=(f"{source_id}-span",),
                    scope="Basic greetings",
                ),
            )
        ),
        blueprint=Blueprint(
            objective="Greet someone",
            vocabulary=("你好",),
            grammar=(),
            teaching_notes="Start with a greeting.",
            claim_ids=("greeting",),
        ),
        material=Material(
            title_zh="问候",
            title_en=f"Greetings: {concept_id}",
            estimated_minutes=5,
            cards=(
                Card(
                    item_id=f"{concept_id}-card",
                    card_type="example",
                    text_zh="你好",
                    pinyin="nǐ hǎo",
                    meaning_en="Hello",
                    explanation_en="A greeting.",
                    claim_ids=("greeting",),
                ),
            ),
            exercises=(
                Exercise(
                    exercise_id=f"{concept_id}-exercise",
                    exercise_type="meaning_mcq",
                    prompt="What does 你好 mean?",
                    instruction="Choose one answer.",
                    options=("Hello", "Goodbye"),
                    answer="Hello",
                    explanation="A greeting.",
                    claim_ids=("greeting",),
                ),
            ),
            teacher_notes="Synthetic test material.",
        ),
        knowledge_review=review,
        teaching_review=review,
        catalog=Catalog(summary="A synthetic greeting unit", tags=("greeting",)),
    )


def save(store: Workbench, value: Packet, *, approved: bool = True) -> str:
    for source in value.sources:
        store.register(source)
    store.save_spans(value.evidence.spans)
    run_id = store.start(value.digest())
    version = store.save_packet(run_id, value)
    if approved:
        store.approve(version, version, "Human teacher")
    return version


@pytest.fixture
def store(tmp_path: Path) -> Workbench:
    return Workbench(tmp_path / "workbench.db")


def test_batch_dependency_round_trip_and_deterministic_identity(
    store: Workbench, tmp_path: Path
) -> None:
    root = save(store, packet("z-foundation"))
    dependent = save(store, packet("a-dependent", ("z-foundation",)))
    final = save(store, packet("b-final", ("a-dependent", "z-foundation")))
    service = PublicationService(store)
    folder = service.export_many((final, dependent, root), tmp_path / "releases")
    assert service.export_many((root, final, dependent), tmp_path / "releases") == folder
    manifest = ReleaseManifest.model_validate_json((folder / "manifest.json").read_text())
    assert [(unit.concept_id, unit.sequence_no) for unit in manifest.units] == [
        ("z-foundation", 1),
        ("a-dependent", 2),
        ("b-final", 3),
    ]
    assert [unit.version_id for unit in manifest.units] == [root, dependent, final]
    assert len((folder / "materials.jsonl").read_text().splitlines()) == 3
    assert "RAW SOURCE SENTINEL" not in (folder / "materials.md").read_text()
    reports = json.loads((folder / "review-report.json").read_text())
    assert [unit["version_id"] for unit in reports["units"]] == [root, dependent, final]
    engine = create_engine(f"sqlite:///{folder / 'materials.db'}")
    try:
        repository = ContentRepository(sessionmaker(bind=engine))
        assert [concept.concept_id for concept in repository.list_concepts()] == [
            "z-foundation",
            "a-dependent",
            "b-final",
        ]
        assert repository.get_prerequisites() == {
            "a-dependent": frozenset({"z-foundation"}),
            "b-final": frozenset({"z-foundation", "a-dependent"}),
        }
        for concept in ("z-foundation", "a-dependent", "b-final"):
            assert repository.get_teaching_cards(concept)[0].prompt_zh == "你好"
            assert repository.get_exercises(concept)[0].answer == {"value": "Hello"}
    finally:
        engine.dispose()
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM release_versions").fetchone()[0] == 3
        assert {row[0] for row in db.execute("SELECT state FROM versions")} == {"published"}


def test_published_singleton_can_be_reused_in_a_larger_release(
    store: Workbench, tmp_path: Path
) -> None:
    root = save(store, packet("root"))
    dependent = save(store, packet("dependent", ("root",)))
    service = PublicationService(store)
    single = service.export(root, tmp_path / "releases")
    assert single.name == root
    batch = service.export_many((dependent, root), tmp_path / "releases")
    assert batch != single
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM releases").fetchone()[0] == 2
        assert (
            db.execute(
                "SELECT COUNT(*) FROM release_versions WHERE version_id=?", (root,)
            ).fetchone()[0]
            == 2
        )


def test_publication_and_revocation_update_every_run_sharing_a_version(
    store: Workbench, tmp_path: Path
) -> None:
    value = packet("shared")
    version = save(store, value)
    second_run = store.start("second-run-same-output")
    assert store.save_packet(second_run, value) == version
    PublicationService(store).export(version, tmp_path / "releases")
    assert {run.state for run in store.runs()} == {"published"}
    store.revoke("fixture", "Human teacher")
    assert {run.state for run in store.runs()} == {"withdrawn"}


def test_every_exact_version_requires_approval(store: Workbench, tmp_path: Path) -> None:
    approved = save(store, packet("root"))
    pending = save(store, packet("dependent", ("root",)), approved=False)
    with pytest.raises(GateError, match="human approval"):
        PublicationService(store).export_many((approved, pending), tmp_path / "releases")
    assert store.version_state(approved) == "approved"
    assert store.version_state(pending) == "awaiting_approval"
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM releases").fetchone()[0] == 0


def test_individually_passing_reviews_can_fail_the_conservative_release_gate(
    store: Workbench, tmp_path: Path
) -> None:
    original = packet("review-disagreement")
    value = original.model_copy(
        update={
            "knowledge_review": original.knowledge_review.model_copy(update={"accuracy": 3}),
            "teaching_review": original.teaching_review.model_copy(update={"evidence": 3}),
        }
    )
    assert value.knowledge_review.passes and value.teaching_review.passes
    assert not value.quality_passes
    version = save(store, value, approved=False)
    with pytest.raises(GateError, match="independent reviews"):
        store.approve(version, version, "Human teacher")
    with pytest.raises(GateError, match="combined quality gates"):
        PublicationService(store).export(version, tmp_path / "releases")


def test_changed_approval_digest_blocks_batch(store: Workbench, tmp_path: Path) -> None:
    first = save(store, packet("first"))
    second = save(store, packet("second"))
    with store.connection() as db:
        db.execute("UPDATE approvals SET digest=? WHERE version_id=?", ("0" * 64, second))
    with pytest.raises(GateError, match="human approval"):
        PublicationService(store).export_many((first, second), tmp_path / "releases")


def test_modified_packet_body_cannot_retain_approval(store: Workbench, tmp_path: Path) -> None:
    original = packet("root")
    version = save(store, original)
    changed = original.model_copy(update={"catalog": Catalog(summary="Changed", tags=())})
    with store.connection() as db:
        db.execute("UPDATE versions SET body=? WHERE id=?", (changed.model_dump_json(), version))
    with pytest.raises(GateError, match="immutable version ID"):
        PublicationService(store).export(version, tmp_path / "releases")


def test_source_changes_are_rechecked_at_publication(store: Workbench, tmp_path: Path) -> None:
    value = packet("root")
    version = save(store, value)
    changed = value.sources[0].model_copy(update={"title": "Unreviewed attribution"})
    with store.connection() as db:
        db.execute(
            "UPDATE sources SET body=? WHERE id=?", (changed.model_dump_json(), changed.source_id)
        )
    with pytest.raises(GateError, match="changed after material review"):
        PublicationService(store).export(version, tmp_path / "releases")


def test_source_revocation_withdraws_batch_even_for_nonrepresentative_member(
    store: Workbench, tmp_path: Path
) -> None:
    first = save(store, packet("first", source_id="first-source"))
    second = save(store, packet("second", source_id="second-source"))
    service = PublicationService(store)
    service.export(first, tmp_path / "releases")
    batch = service.export_many((second, first), tmp_path / "releases")
    store.revoke("second-source", "Human teacher")
    with store.connection() as db:
        assert (
            db.execute("SELECT state FROM releases WHERE id=?", (batch.name,)).fetchone()[0]
            == "withdrawn"
        )
        assert (
            db.execute("SELECT state FROM releases WHERE id=?", (first,)).fetchone()[0]
            == "available"
        )
    with pytest.raises(GateError):
        service.export_many((first, second), tmp_path / "releases")


@pytest.mark.parametrize("duplicate", ["concept", "card", "exercise", "cross_type"])
def test_duplicate_identifiers_are_rejected(
    store: Workbench, tmp_path: Path, duplicate: str
) -> None:
    first_packet = packet("first")
    second_packet = packet("second")
    if duplicate == "concept":
        second_packet = second_packet.model_copy(update={"brief": first_packet.brief})
    elif duplicate == "card":
        second_packet = second_packet.model_copy(
            update={
                "material": second_packet.material.model_copy(
                    update={
                        "cards": (
                            second_packet.material.cards[0].model_copy(
                                update={"item_id": "first-card"}
                            ),
                        ),
                    }
                )
            }
        )
    else:
        item_id = "first-card" if duplicate == "cross_type" else "first-exercise"
        second_packet = second_packet.model_copy(
            update={
                "material": second_packet.material.model_copy(
                    update={
                        "exercises": (
                            second_packet.material.exercises[0].model_copy(
                                update={"exercise_id": item_id}
                            ),
                        ),
                    }
                )
            }
        )
    first, second = save(store, first_packet), save(store, second_packet)
    with pytest.raises(GateError, match="duplicate"):
        PublicationService(store).export_many((first, second), tmp_path / "releases")


def test_missing_transitive_prerequisite_blocks_publication(
    store: Workbench, tmp_path: Path
) -> None:
    middle = save(store, packet("middle", ("root",)))
    last = save(store, packet("last", ("middle",)))
    with pytest.raises(GateError, match="every prerequisite concept: root"):
        PublicationService(store).export_many((last, middle), tmp_path / "releases")


@pytest.mark.parametrize("self_cycle", [False, True])
def test_prerequisite_cycles_are_rejected(
    store: Workbench, tmp_path: Path, self_cycle: bool
) -> None:
    first = save(store, packet("first", ("first" if self_cycle else "second",)))
    versions = (first,) if self_cycle else (first, save(store, packet("second", ("first",))))
    with pytest.raises(GateError, match="cycles"):
        PublicationService(store).export_many(versions, tmp_path / "releases")


def test_empty_or_duplicate_version_selection_is_rejected(store: Workbench, tmp_path: Path) -> None:
    version = save(store, packet("root"))
    service = PublicationService(store)
    with pytest.raises(GateError, match="distinct version IDs"):
        service.export_many((), tmp_path / "releases")
    with pytest.raises(GateError, match="distinct version IDs"):
        service.export_many((version, version), tmp_path / "releases")


def test_failed_build_leaves_no_partial_release(
    store: Workbench, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = save(store, packet("first")), save(store, packet("second"))

    def fail_replace(source: Path, target: Path) -> None:
        raise OSError("Injected filesystem failure")

    monkeypatch.setattr("goalcoach.materials.publication.os.replace", fail_replace)
    with pytest.raises(StorageError, match="Release build failed"):
        PublicationService(store).export_many((first, second), tmp_path / "releases")
    assert not list((tmp_path / "releases").iterdir())
    assert store.version_state(first) == "approved"
    assert store.version_state(second) == "approved"
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM releases").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM release_versions").fetchone()[0] == 0


def test_manifest_member_tampering_is_detected(store: Workbench, tmp_path: Path) -> None:
    first, second = save(store, packet("first")), save(store, packet("second"))
    folder = PublicationService(store).export_many((first, second), tmp_path / "releases")
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["units"][0]["version_id"] = "0" * 64
    (folder / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(GateError, match="identity"):
        PublicationService.verify(folder)


def test_legacy_singleton_manifests_remain_verifiable(store: Workbench, tmp_path: Path) -> None:
    version = save(store, packet("root"))
    folder = PublicationService(store).export(version, tmp_path / "releases")
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["schema_version"] = 1
    del manifest["units"]
    with sqlite3.connect(folder / "materials.db") as db:
        db.execute("UPDATE release_manifest SET schema_version=1")
        db.execute("DROP TABLE release_units")
    manifest["files"]["materials.db"] = hashlib.sha256(
        (folder / "materials.db").read_bytes()
    ).hexdigest()
    (folder / "manifest.json").write_text(json.dumps(manifest))
    PublicationService.verify(folder)
    assert PublicationService(store).export(version, tmp_path / "releases") == folder


def test_manifest_schema_downgrade_is_rejected(store: Workbench, tmp_path: Path) -> None:
    version = save(store, packet("root"))
    folder = PublicationService(store).export(version, tmp_path / "releases")
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["schema_version"] = 1
    del manifest["units"]
    (folder / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(GateError, match="Database release identity"):
        PublicationService.verify(folder)


def test_prerequisites_have_database_foreign_key_integrity(
    store: Workbench, tmp_path: Path
) -> None:
    first = save(store, packet("first"))
    second = save(store, packet("second", ("first",)))
    folder = PublicationService(store).export_many((second, first), tmp_path / "releases")
    with sqlite3.connect(folder / "materials.db") as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute(
            "SELECT concept_id,prerequisite_id FROM concept_prerequisites"
        ).fetchall() == [("second", "first")]
