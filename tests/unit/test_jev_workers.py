"""Verify finite decision composition and the existing learning loop contracts."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from goalcoach.agents.jev_planning import JevPlanningWorker
from goalcoach.agents.jev_teaching import JevTeachingWorker
from goalcoach.application.decisions.contracts import (
    ChoiceAnswer,
    DecisionError,
    DecisionRequest,
    DecisionResponse,
)
from goalcoach.domain.enums import PlanItemKind
from goalcoach.domain.models import LearnerState, LearningGoal
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.llm.jev_client import JevClient


class FakeDecisions:
    def __init__(self, confidence: float = 1) -> None:
        self.requests: list[DecisionRequest] = []
        self.confidence = confidence

    async def decide(self, request: DecisionRequest) -> DecisionResponse:
        self.requests.append(request)
        answers = {}
        for key, q in request.questions.items():
            selected = next(iter(q.criteria))
            if key.startswith("kind_"):
                selected = "new"
            if key.startswith("duration_"):
                selected = "5"
            answers[key] = ChoiceAnswer(
                type="choice",
                choice=selected,
                confidence=self.confidence,
                probabilities={k: float(k == selected) for k in q.criteria},
            )
        return DecisionResponse(model="jev-test", answers=answers)


class Content:
    def __init__(self) -> None:
        self.concepts = [
            SimpleNamespace(
                concept_id=f"c{i}",
                communicative_goal=f"Capability {i}",
                title_en=f"Topic {i}",
                sequence_no=i,
                hsk_level=1,
                grammar_focus=["grammar"],
                vocabulary_focus=["word"],
            )
            for i in (1, 2, 3)
        ]
        self.cards = [
            SimpleNamespace(
                card_id=f"card{i}",
                prompt_zh="你好",
                pinyin="nǐ hǎo",
                meaning_en="hello",
                explanation_en="Use this greeting.",
                example_zh="你好",
                example_pinyin="nǐ hǎo",
                example_en="Hello",
            )
            for i in (1, 2)
        ]
        self.exercises = [
            SimpleNamespace(
                exercise_id=f"e{i}",
                concept_id="c1",
                prompt="Choose a greeting",
                instruction="Choose the correct meaning",
                exercise_type="mcq",
                options=["Hello", "Goodbye"],
            )
            for i in (1, 2)
        ]

    def list_all_concepts(self, **kwargs: object):
        return self.concepts

    def get_all_prerequisites(self):
        return {"c2": frozenset({"c1"})}

    def get_concept(self, cid: str):
        return next(c for c in self.concepts if c.concept_id == cid)

    def get_teaching_cards(self, cid: str):
        return self.cards

    def get_exercises_for_concept(self, cid: str, **kwargs: object):
        return self.exercises


class NoPlanningFallback:
    enable_prerequisites = False

    async def create_plan(self, *args: object, **kwargs: object):
        raise AssertionError("Unexpected LLM call")


class NoTeachingFallback:
    async def teach_concept(self, *args: object, **kwargs: object):
        raise AssertionError("Unexpected LLM call")


@pytest.mark.asyncio
async def test_jev_roadmap_daily_budget_and_remediation() -> None:
    client = FakeDecisions()
    state = LearnerState(
        learner_id="jev-test",
        goal=LearningGoal(title="Travel", target_hsk_level=1, daily_available_minutes=10),
    )
    worker = JevPlanningWorker(client, NoPlanningFallback())  # type: ignore[arg-type]
    result = await worker.create_plan(state, Content(), allow_roadmap_changes=True)  # type: ignore[arg-type]
    assert result.roadmap_concept_ids == ["c1", "c2", "c3"]
    assert sum(i.estimated_minutes for i in result.ordered_items) == 10
    assert len(client.requests) == 1
    assert "coverage" not in client.requests[0].questions
    state.roadmap_concept_ids = ["c2", "c1", "c3"]
    state.roadmap_coverage_rationale = "Existing coverage"
    state.remediation_counters = {"c1": 2}
    state.today_studied_concept_ids = ["c1", "c2"]
    result = await worker.create_plan(state, Content())  # type: ignore[arg-type]
    assert result.roadmap_concept_ids == state.roadmap_concept_ids
    assert result.ordered_items[0].concept_id == "c1"
    assert result.ordered_items[0].kind == PlanItemKind.REMEDIAL
    assert all(i.concept_id != "c2" for i in result.ordered_items)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("enable_prerequisites", "add_missing_quantity", "expected_roadmap"),
    [
        (False, False, ["hsk1_c15"]),
        (True, False, ["hsk1_c14", "hsk1_c15"]),
        (False, True, ["hsk1_c15", "hsk1_c16"]),
        (True, True, ["hsk1_c14", "hsk1_c15", "hsk1_c16"]),
    ],
)
async def test_jev_roadmap_excludes_optional_and_honors_prerequisite_switch(
    enable_prerequisites: bool, add_missing_quantity: bool, expected_roadmap: list[str]
) -> None:
    class NumberContent(Content):
        def __init__(self) -> None:
            super().__init__()
            for concept, cid, purpose in zip(
                self.concepts,
                ("hsk1_c14", "hsk1_c15", "hsk1_c16"),
                ("Say also or all", "Recognize and use basic numbers", "Ask about quantities"),
                strict=True,
            ):
                concept.concept_id = cid
                concept.communicative_goal = purpose

        def get_all_prerequisites(self):
            return {
                "hsk1_c15": frozenset({"hsk1_c14"}),
                "hsk1_c16": frozenset({"hsk1_c15"}),
            }

    class SelectiveDecisions(FakeDecisions):
        async def decide(self, request: DecisionRequest) -> DecisionResponse:
            response = await super().decide(request)
            answers = dict(response.answers)
            for index, choice in enumerate(("optional", "required", "irrelevant")):
                key = f"include_{index}"
                if key in answers:
                    answers[key] = ChoiceAnswer(
                        type="choice",
                        choice=choice,
                        confidence=1,
                        probabilities={
                            option: float(option == choice)
                            for option in request.questions[key].criteria
                        },
                    )
            if add_missing_quantity and "missing_1" in answers:
                answers["missing_1"] = ChoiceAnswer(
                    type="choice",
                    choice="add",
                    confidence=1,
                    probabilities={"skip": 0, "add": 1},
                )
            return DecisionResponse(model=response.model, answers=answers)

    class Fallback(NoPlanningFallback):
        pass

    fallback = Fallback()
    fallback.enable_prerequisites = enable_prerequisites
    client = SelectiveDecisions()
    result = await JevPlanningWorker(client, fallback).create_plan(
        LearnerState(
            learner_id="numbers",
            goal=LearningGoal(title="I want to learn numbers", target_hsk_level=1),
        ),
        NumberContent(),
        allow_roadmap_changes=True,
    )  # type: ignore[arg-type]
    assert result.roadmap_concept_ids == expected_roadmap
    assert len(client.requests) == 2
    assert set(client.requests[1].questions) == {"missing_0", "missing_1"}
    assert json.loads(client.requests[1].state)["selected_courses"][0]["id"] == "hsk1_c15"
    assert result.metadata["jev_added_missing_course_ids"] == (
        ["hsk1_c16"] if add_missing_quantity else []
    )
    assert ("hsk1_c16" in result.roadmap_coverage_rationale) == add_missing_quantity
    assert "directly necessary" in client.requests[0].questions["include_1"].instructions


@pytest.mark.asyncio
async def test_jev_teaching_excludes_completed_and_attaches_canonical_exercise() -> None:
    state = LearnerState(
        learner_id="jev-teaching",
        goal=LearningGoal(title="Travel", target_hsk_level=1),
        today_completed_exercise_ids=["e1"],
    )
    client = FakeDecisions(confidence=0.2)
    result = await JevTeachingWorker(client, NoTeachingFallback()).teach_concept(
        "c1", state, Content()
    )  # type: ignore[arg-type]
    assert result.exercise_payload["exercise_id"] == "e2"
    assert "Use this greeting." in result.content
    assert "你好" in result.content
    assert result.metadata["provider"] == "typesafe:jev-test"
    assert len(client.requests) == 1


@pytest.mark.asyncio
async def test_free_question_still_uses_tutor() -> None:
    class Tutor:
        async def teach_concept(self, *args: object, **kwargs: object):
            return "tutor-result"

    client = FakeDecisions()
    result = await JevTeachingWorker(client, Tutor()).teach_concept(
        "c1", LearnerState(learner_id="question"), Content(), learner_query="Why?"
    )  # type: ignore[arg-type]
    assert result == "tutor-result"
    assert not client.requests


@pytest.mark.asyncio
async def test_jev_http_contract_and_candidate_validation() -> None:
    from goalcoach.application.decisions.contracts import ChoiceQuestion

    request = DecisionRequest(
        state="private state",
        questions={"pick": ChoiceQuestion(instructions="Choose", criteria={"a": "A", "b": "B"})},
    )

    def respond(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/v1/systemone"
        assert req.headers["authorization"] == "Bearer test-key"
        body = json.loads(req.content)
        assert body["model"] == "typesafe/jev-1.13"
        assert body["questions"]["pick"]["type"] == "choice"
        return httpx.Response(
            200,
            json={
                "id": "gen-dec-test",
                "model": "jev-test",
                "provider": "TypeSafe",
                "answers": {
                    "pick": {
                        "type": "choice",
                        "choice": "a",
                        "confidence": 1,
                        "probabilities": {"a": 1, "b": 0},
                    }
                },
                "usage": {"input_tokens": 12, "output_tokens": 0, "cost": 0.000001},
            },
        )

    settings = Settings(
        _env_file=None,
        jev_api_key=SecretStr("test-key"),
        jev_base_url="https://openrouter.ai/api/v1",
        jev_model="typesafe/jev-1.13",
    )
    assert (
        await JevClient(settings, transport=httpx.MockTransport(respond)).decide(request)
    ).answers["pick"].choice == "a"
    default_settings = Settings(_env_file=None)
    assert default_settings.jev_base_url == "https://openrouter.ai/api/v1"
    assert default_settings.jev_model == "typesafe/jev-1.13"
    with pytest.raises(DecisionError, match="Set GOALCOACH"):
        await JevClient(default_settings).decide(request)


@pytest.mark.asyncio
async def test_low_confidence_decisions_use_probability_ranked_top_items() -> None:
    class Fallback:
        enable_prerequisites = False
        called = False

        async def create_plan(self, *args: object, **kwargs: object):
            self.called = True
            from goalcoach.domain.models import PlanItem, PlanUpdate

            return PlanUpdate(
                daily_allocation_minutes=5,
                ordered_items=[
                    PlanItem(
                        concept_id="c1",
                        kind=PlanItemKind.NEW,
                        objective="Practice",
                        estimated_minutes=5,
                    )
                ],
                adaptation_rationale="Fallback",
                roadmap_concept_ids=["c1"],
                roadmap_coverage_rationale="Fallback coverage",
            )

    class ProbabilityDecisions(FakeDecisions):
        async def decide(self, request: DecisionRequest) -> DecisionResponse:
            response = await super().decide(request)
            answers = dict(response.answers)
            distributions = {
                "priority_0": {"high": 0.2, "medium": 0.5, "low": 0.3},
                "priority_1": {"high": 0.7, "medium": 0.2, "low": 0.1},
                "priority_2": {"high": 0.3, "medium": 0.4, "low": 0.3},
            }
            for key, probabilities in distributions.items():
                answers[key] = ChoiceAnswer(
                    type="choice",
                    choice=max(probabilities, key=lambda option: probabilities[option]),
                    confidence=0.2,
                    probabilities=probabilities,
                )
            return DecisionResponse(model=response.model, answers=answers)

    fallback = Fallback()
    result = await JevPlanningWorker(ProbabilityDecisions(confidence=0.2), fallback).create_plan(
        LearnerState(
            learner_id="uncertain",
            goal=LearningGoal(title="Travel", target_hsk_level=1, daily_available_minutes=5),
        ),
        Content(),
        allow_roadmap_changes=True,
    )  # type: ignore[arg-type]
    assert not fallback.called
    assert result.ordered_items[0].concept_id == "c2"
    assert not result.metadata.get("jev_fallback", False)


@pytest.mark.asyncio
async def test_jev_rejects_out_of_candidate_response_without_logging_inputs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    from goalcoach.application.decisions.contracts import ChoiceQuestion

    request = DecisionRequest(
        state="PRIVATE LEARNER",
        questions={"pick": ChoiceQuestion(instructions="Choose", criteria={"a": "A", "b": "B"})},
    )

    def respond(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "jev-test",
                "answers": {
                    "pick": {
                        "type": "choice",
                        "choice": "x",
                        "confidence": 1,
                        "probabilities": {"x": 1},
                    }
                },
            },
        )

    with caplog.at_level(logging.INFO), pytest.raises(DecisionError, match="outside"):
        await JevClient(
            Settings(_env_file=None, jev_api_key=SecretStr("PRIVATE KEY")),
            transport=httpx.MockTransport(respond),
        ).decide(request)
    assert "PRIVATE" not in caplog.text


@pytest.mark.asyncio
async def test_jev_validation_log_identifies_field_without_response_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    from goalcoach.application.decisions.contracts import ChoiceQuestion

    request = DecisionRequest(
        state="PRIVATE LEARNER",
        questions={"pick": ChoiceQuestion(instructions="Choose", criteria={"a": "A", "b": "B"})},
    )

    def respond(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "PRIVATE RESPONSE",
                "answers": {
                    "pick": {
                        "type": "choice",
                        "choice": "a",
                        "probabilities": {"a": 1, "b": 0},
                    }
                },
            },
        )

    with caplog.at_level(logging.WARNING), pytest.raises(DecisionError, match="ValidationError"):
        await JevClient(
            Settings(_env_file=None, jev_api_key=SecretStr("PRIVATE KEY")),
            transport=httpx.MockTransport(respond),
        ).decide(request)
    assert "answers.pick.confidence:missing" in caplog.text
    assert "status=200" in caplog.text
    assert "response_bytes=" in caplog.text
    assert "PRIVATE" not in caplog.text


@pytest.mark.asyncio
async def test_jev_workers_complete_real_orchestrator_learning_cycle(tmp_path) -> None:
    from goalcoach.application.orchestrator import DeterministicOrchestrator
    from goalcoach.application.progress_service import ProgressService
    from goalcoach.domain.enums import EventType
    from goalcoach.infrastructure.persistence import (
        ContentRepository,
        ContentService,
        create_session_factory,
    )
    from goalcoach.infrastructure.persistence.database import create_learner_schema, get_engine
    from goalcoach.infrastructure.persistence.repositories import SqliteLearnerRepository
    from tests.fakes import FakeGraderComponent

    learner_factory = create_session_factory(f"sqlite:///{tmp_path / 'jev-loop.db'}")
    content_factory = create_session_factory(
        "sqlite:///./data/database1/goalcoach_hsk1_learning.db"
    )
    create_learner_schema(learner_factory)
    repo = SqliteLearnerRepository(learner_factory)
    content = ContentService(ContentRepository(content_factory))
    decisions = FakeDecisions()
    orchestrator = DeterministicOrchestrator(
        learner_repo=repo,
        content_service=content,
        planning_worker=JevPlanningWorker(decisions, NoPlanningFallback()),
        teaching_worker=JevTeachingWorker(decisions, NoTeachingFallback()),
        grader_worker=FakeGraderComponent(),
        progress_service=ProgressService(learner_repo=repo),
    )
    try:
        result = await orchestrator.handle_event(
            EventType.GOAL_CREATED,
            payload={
                "title": "Travel Mandarin",
                "target_hsk_level": 1,
                "daily_available_minutes": 10,
            },
            learner_id="jev-loop",
        )
        assert result.daily_plan
        result = await orchestrator.handle_event(
            EventType.SESSION_STARTED, payload={}, learner_id="jev-loop"
        )
        action = result.teaching_action
        assert action and action.metadata["provider"] == "typesafe:jev-test"
        exercise = content.get_exercise(action.exercise_payload["exercise_id"])
        result = await orchestrator.handle_event(
            EventType.ANSWER_SUBMITTED,
            learner_id="jev-loop",
            payload={
                "concept_id": action.concept_id,
                "exercise_id": exercise.exercise_id,
                "answer": exercise.accepted_answers[0]
                if exercise.accepted_answers
                else "test answer",
            },
        )
        assert result.grading_result
        state = await repo.get("jev-loop")
        assert state.active_session.answer_count == 1
        assert state.roadmap_concept_ids
    finally:
        get_engine(learner_factory).dispose()
        get_engine(content_factory).dispose()
