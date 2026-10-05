"""Independent adversarial checks for evidence, task cancellation, and usage history."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path
from typing import TypeVar

import pytest

from goalcoach.materials.agents import MeasuredResult
from goalcoach.materials.models import (
    AgentError,
    Catalog,
    Claim,
    Claims,
    Evidence,
    GateError,
    Record,
    Role,
    Source,
    Span,
    UsageRecord,
)
from goalcoach.materials.store import Workbench
from goalcoach.materials.workflow import ProductionWorkflow, validate_evidence

T = TypeVar("T", bound=Record)


class MeasuredFixtureRunner:
    identity = "measured-fixture-v1"

    def __init__(self) -> None:
        self.calls = 0
        self.fail = False

    async def run(self, role: Role, output: type[T], inputs: tuple[Record, ...]) -> T:
        return (await self.run_metered(role, output, inputs)).output

    async def run_metered(
        self, role: Role, output: type[T], inputs: tuple[Record, ...]
    ) -> MeasuredResult[T]:
        self.calls += 1
        if self.fail:
            raise AgentError("Injected model boundary failure")
        return MeasuredResult(
            output=output.model_validate({"summary": "A test catalog", "tags": []}),
            usage=UsageRecord(
                input_tokens=100,
                output_tokens=50,
                estimated_cost_usd=Decimal("0.0003"),
                model="test-model",
            ),
        )


class WaitingFixtureRunner:
    identity = "waiting-fixture-v1"

    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def run(self, role: Role, output: type[T], inputs: tuple[Record, ...]) -> T:
        self.entered.set()
        await self.release.wait()
        return output.model_validate({"summary": "A test catalog", "tags": []})


@pytest.fixture
def store(tmp_path: Path) -> Workbench:
    return Workbench(tmp_path / "workbench.db")


@pytest.mark.asyncio
async def test_cache_hits_preserve_usage_without_rebilling(store: Workbench) -> None:
    runner = MeasuredFixtureRunner()
    workflow = ProductionWorkflow(store, runner)
    run_id = store.start("cache-test")
    first = await workflow.step(run_id, Role.CATALOG, Catalog, ())
    second = await workflow.step(run_id, Role.CATALOG, Catalog, ())
    assert first == second
    assert runner.calls == 1
    usage = store.usage(run_id)
    assert (usage.attempts, usage.measured_attempts, usage.priced_attempts) == (1, 1, 1)
    assert (usage.input_tokens, usage.output_tokens) == (100, 50)
    assert usage.known_estimated_cost_usd == Decimal("0.0003")


@pytest.mark.asyncio
async def test_failed_attempt_remains_explicitly_unmeasured_on_resume(store: Workbench) -> None:
    runner = MeasuredFixtureRunner()
    workflow = ProductionWorkflow(store, runner)
    run_id = store.start("failure-test")
    runner.fail = True
    with pytest.raises(AgentError, match="Injected"):
        await workflow.step(run_id, Role.CATALOG, Catalog, ())
    runner.fail = False
    await workflow.step(run_id, Role.CATALOG, Catalog, ())
    usage = store.usage(run_id)
    assert (usage.attempts, usage.measured_attempts, usage.priced_attempts) == (2, 1, 1)
    assert usage.known_estimated_cost_usd == Decimal("0.0003")
    with store.connection() as db:
        assert {row[0] for row in db.execute("SELECT outcome FROM task_attempts")} == {
            "failed",
            "complete",
        }


@pytest.mark.asyncio
async def test_cancellation_releases_task_for_immediate_retry(store: Workbench) -> None:
    runner = WaitingFixtureRunner()
    workflow = ProductionWorkflow(store, runner)
    run_id = store.start("cancellation-test")
    task = asyncio.create_task(workflow.step(run_id, Role.CATALOG, Catalog, ()))
    await asyncio.wait_for(runner.entered.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    runner.release.set()
    assert (await workflow.step(run_id, Role.CATALOG, Catalog, ())).summary == "A test catalog"
    assert store.usage(run_id).attempts == 2
    with store.connection() as db:
        assert [row[0] for row in db.execute("SELECT state FROM tasks")] == ["complete"]
        assert {row[0] for row in db.execute("SELECT outcome FROM task_attempts")} == {
            "failed",
            "complete",
        }


def test_expired_worker_cannot_overwrite_new_owner_result(store: Workbench) -> None:
    run_id = store.start("lease-test")
    previous = store.claim_task("task", run_id, Role.CATALOG, 30)
    with store.connection() as db:
        db.execute("UPDATE tasks SET lease_until=0 WHERE key='task'")
    current = store.claim_task("task", run_id, Role.CATALOG, 30)
    value = Catalog(summary="Current owner result", tags=())
    store.finish_task("task", current, value)
    with pytest.raises(GateError, match="ownership changed"):
        store.finish_task("task", previous, Catalog(summary="Obsolete result", tags=()))
    assert store.cached("task", Catalog) == value
    assert store.usage(run_id).attempts == 2


def test_run_lease_excludes_concurrent_resume(store: Workbench) -> None:
    run_id = store.start("run-owner-test")
    owner = store.acquire_run(run_id)
    with pytest.raises(GateError, match="leased by another worker"):
        store.acquire_run(run_id)
    store.renew_run(run_id, owner)
    store.release_run(run_id, owner)
    assert store.acquire_run(run_id) != owner


def test_expired_run_owner_cannot_renew_or_release_successor_lease(store: Workbench) -> None:
    run_id = store.start("run-takeover-test")
    previous = store.acquire_run(run_id)
    with store.connection() as db:
        db.execute("UPDATE run_leases SET lease_until=0 WHERE run_id=?", (run_id,))
    with pytest.raises(GateError, match="expired or changed"):
        store.renew_run(run_id, previous)
    current = store.acquire_run(run_id)
    store.release_run(run_id, previous)
    store.renew_run(run_id, current)
    with pytest.raises(GateError, match="leased by another worker"):
        store.acquire_run(run_id)
    store.release_run(run_id, current)


def source() -> Source:
    return Source(
        source_id="formal",
        title="Original fixture",
        category="textbook",
        publisher="Test author",
        edition="1",
        rights_evidence="Original test work",
        approved_by="Test author",
        allowed_uses=("analysis", "adaptation", "redistribution"),
    )


def span(source_id: str = "formal") -> Span:
    return Span(
        span_id="evidence",
        source_id=source_id,
        locator="page 1",
        text="A supported claim",
        source_hash="fixture-hash",
    )


def claims() -> Claims:
    return Claims(
        claims=(
            Claim(
                claim_id="claim",
                statement="A supported claim",
                span_ids=("evidence",),
                scope="Test context",
            ),
        )
    )


def test_unknown_evidence_source_fails_with_domain_error() -> None:
    with pytest.raises(GateError, match="unregistered source"):
        validate_evidence(claims(), Evidence(spans=(span("missing"),)), (source(),))


@pytest.mark.parametrize("duplicate", ["span", "source", "claim"])
def test_duplicate_evidence_identity_is_rejected(duplicate: str) -> None:
    value = span()
    evidence = Evidence(spans=(value, value) if duplicate == "span" else (value,))
    sources = (source(), source()) if duplicate == "source" else (source(),)
    claim_set = claims()
    if duplicate == "claim":
        claim_set = Claims(claims=(claim_set.claims[0], claim_set.claims[0]))
    with pytest.raises(GateError, match="Duplicate"):
        validate_evidence(claim_set, evidence, sources)


def test_social_sources_cannot_alone_establish_formal_teaching_evidence() -> None:
    social = source().model_copy(update={"category": "professional_social"})
    with pytest.raises(GateError, match="formal teaching evidence"):
        validate_evidence(claims(), Evidence(spans=(span(),)), (social,))
