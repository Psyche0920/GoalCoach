"""Real local review forms preserve approval, batch publication, and browser safety gates."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from goalcoach.materials.dashboard import create_review_app
from goalcoach.materials.models import Decision, UsageRecord
from goalcoach.materials.publication import ReleaseManifest
from goalcoach.materials.store import Workbench
from tests.materials.test_batch_publication import packet, save

ORIGIN = "http://127.0.0.1:8766"


class FormParser(HTMLParser):
    """Read actual HTML form tokens instead of reaching into application internals."""

    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "input" and attributes.get("name") == "csrf_token":
            value = attributes.get("value")
            assert value is not None
            self.tokens.append(value)


def token(client: TestClient, path: str = "/") -> str:
    response = client.get(path)
    assert response.status_code == 200
    parser = FormParser()
    parser.feed(response.text)
    assert len(set(parser.tokens)) == 1
    return parser.tokens[0]


@pytest.fixture
def store(tmp_path: Path) -> Workbench:
    return Workbench(tmp_path / "workbench.db")


@pytest.fixture
def client(store: Workbench, tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_review_app(store, tmp_path / "releases"), base_url=ORIGIN) as value:
        yield value


def test_dashboard_reads_full_packet_history_and_usage_without_writes(
    store: Workbench, client: TestClient, tmp_path: Path
) -> None:
    value = packet("greeting")
    malicious = '<script>alert("source")</script>'
    value = value.model_copy(
        update={"material": value.material.model_copy(update={"teacher_notes": malicious})}
    )
    version = save(store, value, approved=False)
    run_id = store.versions()[0].run_id
    owner = store.claim_task("dispute-1", run_id, "dispute_arbitration", 3)
    store.finish_task(
        "dispute-1",
        owner,
        Decision(
            decision="revise",
            rationale="Resolve a disputed greeting register.",
            evidence_span_ids=(),
            revision_instructions="Clarify register before another independent review.",
        ),
        UsageRecord(
            input_tokens=100,
            output_tokens=20,
            estimated_cost_usd=Decimal("0.003"),
            model="private-provider-model-name",
        ),
    )
    before = store.path.read_bytes()
    index = client.get("/")
    detail = client.get(f"/versions/{version}")
    run = client.get(f"/runs/{run_id}")
    assert index.status_code == detail.status_code == run.status_code == 200
    assert "USD 0.003000" in index.text and "100 input tokens" in index.text
    assert "private-provider-model-name" not in index.text
    assert "RAW SOURCE SENTINEL" in detail.text
    assert (
        "dispute_arbitration" in detail.text
        and "Resolve a disputed greeting register" in detail.text
    )
    assert "Resolve a disputed greeting register" in run.text
    assert "<script>" not in detail.text and "&lt;script&gt;" in detail.text
    assert "Complete immutable packet" in detail.text and version in detail.text
    assert detail.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in detail.headers["content-security-policy"]
    assert client.get("/approve").status_code == 405
    assert client.get("/publish").status_code == 405
    assert store.version_state(version) == "awaiting_approval"
    assert store.path.read_bytes() == before
    assert not (tmp_path / "releases").exists()


def test_approval_requires_exact_reviewed_hash_and_identified_teacher(
    store: Workbench, client: TestClient
) -> None:
    version = save(store, packet("greeting"), approved=False)
    fields = {
        "csrf_token": token(client, f"/versions/{version}"),
        "version_id": version,
        "expected_hash": "0" * 64,
        "reviewer": "Human teacher",
    }
    stale = client.post("/approve", data=fields, headers={"Origin": ORIGIN})
    assert stale.status_code == 409 and "hash" in stale.text
    assert store.version_state(version) == "awaiting_approval"
    fields["expected_hash"] = version
    fields["reviewer"] = "   "
    assert client.post("/approve", data=fields, headers={"Origin": ORIGIN}).status_code == 422
    fields["reviewer"] = "Human teacher"
    approved = client.post("/approve", data=fields, headers={"Origin": ORIGIN})
    assert approved.status_code == 200 and "Version approved" in approved.text
    assert store.version_state(version) == "approved"
    with store.connection() as db:
        row = db.execute(
            "SELECT digest,reviewer FROM approvals WHERE version_id=?", (version,)
        ).fetchone()
        assert row is not None and tuple(row) == (version, "Human teacher")
    assert client.post("/approve", data=fields, headers={"Origin": ORIGIN}).status_code == 409


@pytest.mark.parametrize("csrf", [None, "invalid", "非ASCII"])
def test_missing_or_invalid_csrf_cannot_approve(
    store: Workbench, client: TestClient, csrf: str | None
) -> None:
    version = save(store, packet("greeting"), approved=False)
    fields = {"version_id": version, "expected_hash": version, "reviewer": "Teacher"}
    if csrf is not None:
        fields["csrf_token"] = csrf
    assert client.post("/approve", data=fields, headers={"Origin": ORIGIN}).status_code == 403
    assert store.version_state(version) == "awaiting_approval"


@pytest.mark.parametrize(
    "origin", [None, "https://external.example", "null", "http://localhost:8766"]
)
def test_writes_require_exact_same_origin(
    store: Workbench, client: TestClient, origin: str | None
) -> None:
    version = save(store, packet("greeting"), approved=False)
    fields = {
        "csrf_token": token(client),
        "version_id": version,
        "expected_hash": version,
        "reviewer": "Teacher",
    }
    headers = {} if origin is None else {"Origin": origin}
    assert client.post("/approve", data=fields, headers=headers).status_code == 403
    assert store.version_state(version) == "awaiting_approval"


@pytest.mark.parametrize(
    "host",
    [
        "external.example",
        "127.0.0.1.external.example",
        "user@localhost",
        "localhost:0",
        "localhost:99999",
    ],
)
def test_external_or_invalid_host_is_rejected(client: TestClient, host: str) -> None:
    assert client.get("/", headers={"Host": host}).status_code == 403
    assert (
        client.post("/publish", headers={"Host": host, "Origin": f"http://{host}"}).status_code
        == 403
    )


@pytest.mark.parametrize("host", ["localhost:8766", "127.0.0.1:8766", "[::1]:8766"])
def test_loopback_hosts_are_supported(client: TestClient, host: str) -> None:
    assert client.get("/", headers={"Host": host}).status_code == 200


def test_csrf_token_changes_when_dashboard_restarts(store: Workbench, tmp_path: Path) -> None:
    with TestClient(create_review_app(store, tmp_path / "releases"), base_url=ORIGIN) as first:
        first_token = token(first)
    with TestClient(create_review_app(store, tmp_path / "releases"), base_url=ORIGIN) as second:
        second_token = token(second)
        assert first_token != second_token
        response = second.post(
            "/publish", data={"csrf_token": first_token}, headers={"Origin": ORIGIN}
        )
        assert response.status_code == 403


def test_publish_form_invokes_dependency_complete_batch_export(
    store: Workbench, client: TestClient, tmp_path: Path
) -> None:
    root = save(store, packet("foundation"), approved=False)
    dependent = save(store, packet("dependent", ("foundation",)), approved=False)
    csrf = token(client)
    for version in (root, dependent):
        response = client.post(
            "/approve",
            data={
                "csrf_token": csrf,
                "version_id": version,
                "expected_hash": version,
                "reviewer": "Teacher",
            },
            headers={"Origin": ORIGIN},
        )
        assert response.status_code == 200
    content = urlencode({"csrf_token": csrf, "version_ids": (dependent, root)}, doseq=True)
    response = client.post(
        "/publish",
        content=content,
        headers={"Origin": ORIGIN, "Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200 and "Published 2 approved" in response.text
    folders = list((tmp_path / "releases").iterdir())
    assert len(folders) == 1
    manifest = ReleaseManifest.model_validate_json((folders[0] / "manifest.json").read_text())
    assert [unit.version_id for unit in manifest.units] == [root, dependent]
    assert store.version_state(root) == store.version_state(dependent) == "published"


def test_publish_does_not_approve_or_accept_unapproved_versions(
    store: Workbench, client: TestClient, tmp_path: Path
) -> None:
    version = save(store, packet("greeting"), approved=False)
    response = client.post(
        "/publish",
        data={"csrf_token": token(client), "version_ids": version},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 409
    assert store.version_state(version) == "awaiting_approval"
    assert not list((tmp_path / "releases").glob("*/materials.db"))


def test_form_rejects_duplicate_tokens_and_unexpected_fields(client: TestClient) -> None:
    csrf = token(client)
    headers = {"Origin": ORIGIN, "Content-Type": "application/x-www-form-urlencoded"}
    assert (
        client.post(
            "/publish", content=urlencode({"csrf_token": (csrf, csrf)}, doseq=True), headers=headers
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/publish",
            content=urlencode({"csrf_token": csrf, "release_root": "/tmp/unapproved"}),
            headers=headers,
        ).status_code
        == 422
    )
    assert client.post("/publish", content="x" * 32769, headers=headers).status_code == 413
    assert (
        client.post("/publish", json={"csrf_token": csrf}, headers={"Origin": ORIGIN}).status_code
        == 415
    )


def test_unknown_runs_and_versions_return_not_found(client: TestClient) -> None:
    assert client.get("/versions/unknown").status_code == 404
    assert client.get("/runs/unknown").status_code == 404
