"""Tests for validation of agent-authored curriculum ordering."""

from types import SimpleNamespace

import pytest
from pydantic_ai import ModelRetry

from goalcoach.agents.planning_agent import (
    validate_agent_roadmap,
    validate_planning_output,
)
from goalcoach.domain.enums import PlanItemKind
from goalcoach.domain.models import PlanItem, PlanUpdate


def test_agent_roadmap_order_is_preserved() -> None:
    concepts = ["c1", "c2", "c3"]

    ordered = validate_agent_roadmap(["c3", "c1", "c2"], concepts)

    assert ordered == ["c3", "c1", "c2"]


def test_invalid_and_duplicate_ids_are_removed_without_expanding_scope() -> None:
    concepts = ["c1", "c2", "c3"]

    assert validate_agent_roadmap(["unknown", "c2", "c2"], concepts) == ["c2"]


def _planning_context(concept_count: int = 12) -> object:
    concepts = [SimpleNamespace(concept_id=f"c{index}") for index in range(1, concept_count + 1)]
    content_service = SimpleNamespace(list_all_concepts=lambda: concepts)
    deps = SimpleNamespace(
        content_service=content_service,
        state=SimpleNamespace(roadmap_concept_ids=[], remediation_counters={}),
        allow_roadmap_changes=True,
    )
    return SimpleNamespace(deps=deps)


def _plan(roadmap_ids: list[str], daily_id: str = "c1") -> PlanUpdate:
    return PlanUpdate(
        daily_allocation_minutes=5,
        ordered_items=[
            PlanItem(
                concept_id=daily_id,
                kind=PlanItemKind.NEW,
                objective="Practice the selected concept",
                estimated_minutes=5,
            )
        ],
        adaptation_rationale="Selected directly from the learner goal.",
        roadmap_concept_ids=roadmap_ids,
        roadmap_coverage_rationale="Covers every capability named by the free-form goal.",
    )


def test_agent_may_choose_more_than_the_minimum_roadmap_size() -> None:
    output = _plan([f"c{index}" for index in range(1, 11)])

    assert validate_planning_output(_planning_context(), output) is output  # type: ignore[arg-type]


def test_agent_output_retries_when_roadmap_has_fewer_than_eight_concepts() -> None:
    with pytest.raises(ModelRetry, match="at least 8"):
        validate_planning_output(  # type: ignore[arg-type]
            _planning_context(),
            _plan([f"c{index}" for index in range(1, 8)]),
        )


def test_agent_output_retries_when_daily_item_is_outside_roadmap() -> None:
    with pytest.raises(ModelRetry, match="ordered_items"):
        validate_planning_output(  # type: ignore[arg-type]
            _planning_context(),
            _plan([f"c{index}" for index in range(1, 9)], daily_id="c9"),
        )
