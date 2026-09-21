"""Tests that Roadmap and Daily Plan are projections of the same learner state."""

from types import SimpleNamespace

from apps.api.routes.learning import build_roadmap_projection
from goalcoach.domain.enums import PlanItemKind
from goalcoach.domain.models import DailyPlan, LearnerState, PlanItem


def _concept(concept_id: str, sequence_no: int) -> SimpleNamespace:
    return SimpleNamespace(
        concept_id=concept_id,
        hsk_level=1,
        sequence_no=sequence_no,
        slug=concept_id,
        title_zh=concept_id,
        title_en=concept_id,
        concept_type="grammar",
        communicative_goal="Communicate",
        grammar_focus=[],
        vocabulary_focus=[],
        difficulty=1,
        estimated_minutes=5,
        metadata_json={},
    )


def test_roadmap_embeds_items_from_the_persisted_daily_plan() -> None:
    plan_item = PlanItem(
        concept_id="c2",
        kind=PlanItemKind.NEW,
        objective="Learn c2",
        estimated_minutes=5,
    )
    state = LearnerState(
        learner_id="learner-1",
        roadmap_concept_ids=["c2", "c1"],
        active_plan=DailyPlan(
            learner_id="learner-1",
            items=[plan_item],
            rationale="Agent-selected plan",
        ),
    )

    roadmap = build_roadmap_projection(state, [_concept("c1", 1), _concept("c2", 2)])

    assert [node["conceptId"] for node in roadmap] == ["c2", "c1"]
    assert roadmap[0]["dailyPlanItem"] is plan_item
    assert roadmap[1]["dailyPlanItem"] is None
