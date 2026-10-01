"""Regression coverage for same-day remediation and agent failure handling."""

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from pydantic_ai import ModelRetry

from goalcoach.agents.planning_agent import (
    AgentPlanUpdate,
    PlanningDeps,
    PlanningWorker,
    validate_planning_output,
)
from goalcoach.domain.enums import PlanItemKind
from goalcoach.domain.models import LearnerState, LearningGoal, PlanItem
from goalcoach.infrastructure.llm.pydantic_ai_models import AgentOutputError, LLMUnavailableError


@dataclass(frozen=True)
class ConceptStub:
    concept_id: str


class ContentStub:
    def list_all_concepts(
        self,
        hsk_level: int | None = None,
        max_hsk_level: int | None = None,
    ) -> list[ConceptStub]:
        return [ConceptStub("c1"), ConceptStub("c2")]


def remediation_state() -> LearnerState:
    return LearnerState(
        learner_id="remediation-test",
        goal=LearningGoal(title="Basic greetings"),
        roadmap_concept_ids=["c1", "c2"],
        remediation_counters={"c1": 2},
        today_studied_concept_ids=["c1"],
        needs_replanning=True,
    )


def plan(concept_id: str, kind: PlanItemKind) -> AgentPlanUpdate:
    return AgentPlanUpdate(
        daily_allocation_minutes=5,
        ordered_items=[
            PlanItem(
                concept_id=concept_id,
                kind=kind,
                objective="Practice greetings",
                estimated_minutes=5,
            )
        ],
        adaptation_rationale="Address the learner's unresolved errors.",
        roadmap_concept_ids=["c2"],
        roadmap_coverage_rationale="Preserve the goal's greeting sequence.",
    )


def validate(state: LearnerState, output: AgentPlanUpdate) -> AgentPlanUpdate:
    deps = PlanningDeps(state, ContentStub(), False, False)  # type: ignore[arg-type]
    return validate_planning_output(SimpleNamespace(deps=deps), output)  # type: ignore[arg-type]


def test_persisted_roadmap_controls_mandatory_remediation() -> None:
    with pytest.raises(ModelRetry, match="c1"):
        validate(remediation_state(), plan("c2", PlanItemKind.NEW))


@pytest.mark.asyncio
async def test_same_day_remediation_survives_validator_and_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = remediation_state()
    output = validate(state, plan("c1", PlanItemKind.REMEDIAL))
    assert output.roadmap_concept_ids == state.roadmap_concept_ids

    async def run(*args: object, **kwargs: object) -> tuple[object, str]:
        return SimpleNamespace(output=output), "test"

    monkeypatch.setattr("goalcoach.agents.planning_agent.run_with_fallback", run)
    result = await PlanningWorker(agent=object(), enable_prerequisites=False).create_plan(
        state,
        ContentStub(),  # type: ignore[arg-type]
    )
    assert [(item.concept_id, item.kind) for item in result.ordered_items] == [
        ("c1", PlanItemKind.REMEDIAL)
    ]


def test_repeat_exception_does_not_apply_to_resolved_remediation() -> None:
    state = remediation_state()
    state.remediation_counters.clear()
    with pytest.raises(ModelRetry, match="already studied"):
        validate(state, plan("c1", PlanItemKind.REMEDIAL))


@pytest.mark.asyncio
async def test_model_failure_does_not_replace_plan_with_heuristic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(*args: object, **kwargs: object) -> tuple[object, str]:
        raise LLMUnavailableError("Output retries exhausted")

    monkeypatch.setattr("goalcoach.agents.planning_agent.run_with_fallback", fail)
    with pytest.raises(AgentOutputError, match="Retry planning"):
        await PlanningWorker(agent=object(), enable_prerequisites=False).create_plan(
            remediation_state(),
            ContentStub(),  # type: ignore[arg-type]
        )


def test_model_execution_fields_do_not_enter_new_plan() -> None:
    output = AgentPlanUpdate.model_validate(
        {
            "daily_allocation_minutes": 5,
            "ordered_items": [
                {
                    "concept_id": "c1",
                    "kind": "new",
                    "objective": "Practice greetings",
                    "estimated_minutes": 5,
                    "id": "model-generated",
                    "completed": True,
                    "concept_ids": ["unknown"],
                }
            ],
            "adaptation_rationale": "Practice greetings today.",
            "roadmap_concept_ids": ["c1", "c2"],
            "roadmap_coverage_rationale": "Covers greetings and introductions.",
            "metadata": {"unnecessary_catalog": "ignored"},
        }
    )
    result = output.to_domain()
    assert str(result.ordered_items[0].id) != "model-generated"
    assert not result.ordered_items[0].completed
    assert result.ordered_items[0].concept_ids == []
    assert result.metadata == {}
    assert result.roadmap_concept_ids == ["c1", "c2"]
    assert result.ordered_items[0].objective == "Practice greetings"
    schema = AgentPlanUpdate.model_json_schema()
    assert set(schema["$defs"]["AgentPlanItem"]["properties"]) == {
        "concept_id",
        "kind",
        "objective",
        "estimated_minutes",
    }
    assert "metadata" not in schema["properties"]


def test_compact_catalog_preserves_goal_selection_evidence() -> None:
    from goalcoach.agents.planning_agent import get_curriculum_catalog

    concept = SimpleNamespace(
        concept_id="c1",
        title_en="Greetings",
        sequence_no=1,
        difficulty=1,
        communicative_goal="Greet a person and introduce yourself.",
        grammar_focus=["是"],
        vocabulary_focus=["你好"],
        hsk_level=1,
        title_zh="问候",
        metadata_json={"large_unneeded_data": "ignored"},
    )
    service = SimpleNamespace(
        list_all_concepts=lambda **kwargs: [concept],
        get_prerequisites=lambda cid: ["c0"],
    )
    state = LearnerState(
        learner_id="catalog-test", goal=LearningGoal(title="Greetings", target_hsk_level=1)
    )
    context = SimpleNamespace(deps=PlanningDeps(state, service, False, True))
    catalog = get_curriculum_catalog(context)  # type: ignore[arg-type]
    entry = catalog[0].model_dump()
    assert entry["communicative_goal"] == concept.communicative_goal
    assert entry["grammar_focus"] == ["是"]
    assert entry["vocabulary_focus"] == ["你好"]
    assert entry["prerequisites"] == ["c0"]
    assert "metadata" not in entry
    assert "title_zh" not in entry
