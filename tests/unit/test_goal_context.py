"""Tests for preserving free-form goals without categorical mapping."""

from types import SimpleNamespace

import pytest

from goalcoach.agents.planning_agent import PlanningWorker
from goalcoach.domain.enums import PlanItemKind
from goalcoach.domain.models import (
    ConceptMastery,
    LearnerState,
    LearningGoal,
    PlanItem,
    PlanUpdate,
)


def test_free_form_goal_is_preserved_without_category_mapping() -> None:
    title = "I need Mandarin for negotiating renewable-energy contracts in Chengdu"

    assert LearningGoal(title=title).title == title


@pytest.mark.asyncio
async def test_planning_prompt_uses_current_decayed_retention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_prompt = ""

    async def fake_run(_agent: object, prompt: str, deps: object = None) -> tuple[object, str]:
        nonlocal captured_prompt
        captured_prompt = prompt
        return (
            SimpleNamespace(
                output=PlanUpdate(
                    daily_allocation_minutes=5,
                    ordered_items=[
                        PlanItem(
                            concept_id="c1",
                            kind=PlanItemKind.REVIEW,
                            objective="Review c1",
                            estimated_minutes=5,
                        )
                    ],
                    adaptation_rationale="Retention is low.",
                    roadmap_concept_ids=["c1"],
                )
            ),
            "test-provider",
        )

    class ContentStub:
        def list_all_concepts(self, hsk_level: int | None = None) -> list[object]:
            return [SimpleNamespace(concept_id="c1")]

    monkeypatch.setattr(
        "goalcoach.agents.planning_agent.run_with_fallback",
        fake_run,
    )
    monkeypatch.setattr(
        ConceptMastery,
        "current_retention",
        lambda _self, at=None: 0.42,
    )
    state = LearnerState(
        learner_id="retention-planner",
        goal=LearningGoal(title="Travel in China", target_hsk_level=1),
        mastery={
            "c1": ConceptMastery(
                concept_id="c1",
                mastery_score=0.5,
                retention_score=1.0,
            )
        },
    )

    await PlanningWorker(agent=object(), enable_prerequisites=False).create_plan(
        state,
        ContentStub(),  # type: ignore[arg-type]
    )

    assert "'retention': 0.42" in captured_prompt
