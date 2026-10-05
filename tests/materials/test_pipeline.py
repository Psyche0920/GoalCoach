"""Adversarial gates and an actual SQLite round trip with test-only agent fixtures."""

from pathlib import Path
from typing import TypeVar

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from goalcoach.infrastructure.persistence.repositories import ContentRepository
from goalcoach.materials.agents import ModelSettings, PydanticAgentRunner
from goalcoach.materials.ingestion import IngestionService
from goalcoach.materials.models import (
    AgentError,
    Blueprint,
    Brief,
    Card,
    Catalog,
    Claim,
    Claims,
    Decision,
    Evidence,
    Exercise,
    GateError,
    Material,
    Record,
    Review,
    Role,
    Solution,
    Solutions,
    Source,
    SourcePlan,
)
from goalcoach.materials.publication import PublicationService
from goalcoach.materials.store import Workbench
from goalcoach.materials.workflow import ProductionWorkflow, validate_material

T = TypeVar("T", bound=Record)


def source() -> Source:
    return Source(
        source_id="fixture",
        title="Test-only original fixture",
        category="textbook",
        publisher="Test author",
        edition="1",
        rights_evidence="Test fixture, not an official textbook",
        allowed_uses=("analysis", "adaptation", "redistribution"),
        approved_by="test-owner",
    )


def review(verdict: str = "pass") -> Review:
    return Review.model_validate(
        {
            "verdict": verdict,
            "accuracy": 5,
            "teachability": 5,
            "evidence": 5,
            "difficulty": 5,
            "naturalness": 5,
            "issues": [],
            "rationale": "Test fixture review.",
        }
    )


class FixtureRunner:
    identity = "test-only-fixture-v1"

    def __init__(self, dispute: bool = False) -> None:
        self.calls = 0
        self.dispute = dispute
        self.author_calls = 0
        self.blind_seen = False

    async def run(self, role: Role, output: type[T], inputs: tuple[Record, ...]) -> T:
        self.calls += 1
        result: Record
        if output is SourcePlan:
            result = SourcePlan(
                selected_source_ids=("fixture",), rationale="A registered test source."
            )
        elif output is Claims:
            evidence = next(x for x in inputs if isinstance(x, Evidence))
            result = Claims(
                claims=(
                    Claim(
                        claim_id="greeting",
                        statement="你好 is a greeting.",
                        span_ids=(evidence.spans[0].span_id,),
                        scope="Basic greeting",
                    ),
                )
            )
        elif output is Blueprint:
            result = Blueprint(
                objective="Greet someone",
                vocabulary=("你好",),
                grammar=(),
                teaching_notes="Use a greeting.",
                claim_ids=("greeting",),
            )
        elif output is Material:
            self.author_calls += 1
            result = Material(
                title_zh="问候",
                title_en="Greetings",
                estimated_minutes=5,
                cards=(
                    Card(
                        item_id="greeting-card",
                        card_type="example",
                        text_zh="你好",
                        pinyin="nǐ hǎo",
                        meaning_en="Hello",
                        explanation_en="A basic greeting.",
                        claim_ids=("greeting",),
                    ),
                ),
                exercises=(
                    Exercise(
                        exercise_id="greeting-ex",
                        exercise_type="meaning_mcq",
                        prompt="What does 你好 mean?",
                        instruction="Choose the meaning.",
                        options=("Hello", "Goodbye"),
                        answer="Hello",
                        explanation="你好 is a greeting.",
                        claim_ids=("greeting",),
                    ),
                ),
                teacher_notes=f"Test fixture revision {self.author_calls}.",
            )
        elif output is Solutions:
            body = inputs[-1].model_dump_json()
            assert '"answer"' not in body and '"explanation"' not in body
            self.blind_seen = True
            result = Solutions(
                solutions=(
                    Solution(exercise_id="greeting-ex", answer="Hello", rationale="A greeting."),
                )
            )
        elif output is Review:
            result = review(
                "dispute"
                if self.dispute and self.author_calls == 1 and role == Role.KNOWLEDGE
                else "pass"
            )
        elif output is Decision:
            result = Decision(
                decision="revise",
                rationale="Resolve the scope.",
                evidence_span_ids=(),
                revision_instructions="Clarify basic greeting context.",
            )
        elif output is Catalog:
            result = Catalog(summary="Test greeting unit", tags=("greetings",))
        else:
            raise AssertionError(output)
        return output.model_validate_json(result.model_dump_json())


@pytest.fixture
def store(tmp_path: Path) -> Workbench:
    db = Workbench(tmp_path / "workbench.db")
    IngestionService(db).import_text(
        source(), "你好 means Hello.\n你好 means Hello.\nContact x@example.org", "fixture.txt"
    )
    return db


def brief() -> Brief:
    return Brief(
        concept_id="test-greeting",
        objective="Greet someone",
        framework="Test-only curriculum",
        hsk_level=1,
    )


@pytest.mark.asyncio
async def test_full_pipeline_and_goalcoach_compatibility(store: Workbench, tmp_path: Path) -> None:
    runner = FixtureRunner()
    result = await ProductionWorkflow(store, runner).run(brief(), ("fixture",))
    assert result.state == "awaiting_approval" and result.version_id
    assert runner.blind_seen
    publication = PublicationService(store)
    with pytest.raises(GateError, match="human approval"):
        publication.export(result.version_id, tmp_path / "releases")
    with pytest.raises(GateError, match="hash"):
        store.approve(result.version_id, "stale", "Teacher")
    packet = store.packet(result.version_id)
    store.approve(result.version_id, packet.digest(), "Teacher")
    folder = publication.export(result.version_id, tmp_path / "releases")
    assert publication.export(result.version_id, tmp_path / "releases") == folder
    engine = create_engine(f"sqlite:///{folder / 'materials.db'}")
    try:
        repository = ContentRepository(sessionmaker(bind=engine))
        assert repository.list_concepts()[0].concept_id == "test-greeting"
        assert repository.get_teaching_cards("test-greeting")[0].prompt_zh == "你好"
        assert repository.get_exercises("test-greeting")[0].answer == {"value": "Hello"}
        assert (folder / "materials.md").exists()
    finally:
        engine.dispose()
    previous_calls = runner.calls
    resumed = await ProductionWorkflow(store, runner).run(brief(), ("fixture",), result.run_id)
    assert resumed.version_id == result.version_id
    assert resumed.state == "published"
    assert f"run {result.run_id} state=published" in store.status()
    assert runner.calls == previous_calls
    store.revoke("fixture", "Teacher")
    with pytest.raises(GateError):
        publication.export(result.version_id, tmp_path / "releases")
    assert "withdrawn" in store.status()


@pytest.mark.asyncio
async def test_dispute_requires_new_independent_reviews(store: Workbench) -> None:
    runner = FixtureRunner(dispute=True)
    result = await ProductionWorkflow(store, runner).run(brief(), ("fixture",))
    assert result.state == "awaiting_approval"
    assert runner.author_calls == 2


@pytest.mark.asyncio
async def test_budget_is_persistent(store: Workbench) -> None:
    workflow = ProductionWorkflow(store, FixtureRunner(), request_limit=1)
    with pytest.raises(GateError, match="budget"):
        await workflow.run(brief(), ("fixture",))
    assert "requests=1" in store.status()


def test_ingestion_deduplicates_and_redacts(store: Workbench) -> None:
    spans = store.spans()
    assert len(spans) == 2
    assert any("[REDACTED EMAIL]" in s.text for s in spans)
    assert not any("x@example.org" in s.text for s in spans)


def test_source_identity_cannot_be_silently_changed(store: Workbench) -> None:
    with pytest.raises(GateError, match="immutable"):
        store.register(source().model_copy(update={"title": "Changed"}))


def test_no_production_model_fallback() -> None:
    with pytest.raises(AgentError, match="MATERIALS_MODEL"):
        PydanticAgentRunner(ModelSettings(model="", api_key=""))


@pytest.mark.asyncio
async def test_unknown_citations_block_material(store: Workbench) -> None:
    result = await ProductionWorkflow(store, FixtureRunner()).run(brief(), ("fixture",))
    assert result.version_id
    packet = store.packet(result.version_id)
    with pytest.raises(GateError, match="nonexistent"):
        validate_material(
            packet.material,
            Claims(
                claims=(
                    Claim(
                        claim_id="unrelated", statement="Other", span_ids=("unknown",), scope="test"
                    ),
                )
            ),
        )


@pytest.mark.asyncio
async def test_collection_rejects_unapproved_host(store: Workbench) -> None:
    with pytest.raises(GateError, match="HTTPS host"):
        await IngestionService(store).collect(
            source().model_copy(update={"url": "http://localhost/admin"}), frozenset({"localhost"})
        )


@pytest.mark.asyncio
async def test_real_pydanticai_adapter_with_mock_http() -> None:
    import json

    import httpx
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    requests = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        body = json.loads(request.content)
        tool_name = body["tools"][0]["function"]["name"]
        return httpx.Response(
            200,
            json={
                "id": "test-completion",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-test",
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": '{"summary":"Test catalog","tags":["greeting"]}',
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            },
        )

    runner = PydanticAgentRunner(ModelSettings(model="test-model", api_key="test-not-a-secret"))
    await runner.close()
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = AsyncOpenAI(api_key="test-not-a-secret", http_client=http, max_retries=0)
        runner.model = OpenAIChatModel("test-model", provider=OpenAIProvider(openai_client=client))
        result = await runner.run(Role.CATALOG, Catalog, (brief(),))
        assert result.summary == "Test catalog"
        assert requests == 1
        await runner.close()


@pytest.mark.asyncio
async def test_release_tampering_is_detected(store: Workbench, tmp_path: Path) -> None:
    result = await ProductionWorkflow(store, FixtureRunner()).run(brief(), ("fixture",))
    assert result.version_id
    store.approve(result.version_id, result.version_id, "Teacher")
    folder = PublicationService(store).export(result.version_id, tmp_path / "releases")
    (folder / "materials.md").write_text("Tampered content")
    with pytest.raises(GateError, match="integrity"):
        PublicationService.verify(folder)


@pytest.mark.asyncio
async def test_prerequisites_are_not_silently_dropped(store: Workbench, tmp_path: Path) -> None:
    dependent = brief().model_copy(update={"prerequisite_ids": ("missing-concept",)})
    result = await ProductionWorkflow(store, FixtureRunner()).run(dependent, ("fixture",))
    assert result.version_id
    store.approve(result.version_id, result.version_id, "Teacher")
    with pytest.raises(GateError, match="self-contained"):
        PublicationService(store).export(result.version_id, tmp_path / "releases")


@pytest.mark.asyncio
async def test_changed_inputs_cannot_resume_an_existing_run(store: Workbench) -> None:
    workflow = ProductionWorkflow(store, FixtureRunner())
    result = await workflow.run(brief(), ("fixture",))
    with pytest.raises(GateError, match="Resume inputs"):
        await workflow.run(
            brief().model_copy(update={"objective": "Different goal"}), ("fixture",), result.run_id
        )


def test_two_workers_cannot_claim_the_same_task(store: Workbench) -> None:
    run_id = store.start("fixed-input")
    owner = store.claim_task("task", run_id, "test-role", 30)
    with pytest.raises(GateError, match="leased"):
        store.claim_task("task", run_id, "test-role", 30)
    store.finish_task("task", owner, None)
    assert store.claim_task("task", run_id, "test-role", 30) != owner
