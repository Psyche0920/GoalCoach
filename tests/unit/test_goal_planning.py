from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from goalcoach.agents.goal_planning import DeterministicGoalPlanner
from goalcoach.domain.enums import PlanItemKind, PlanStatus
from goalcoach.domain.models import (
    ConceptMastery,
    LearnerState,
    LearningGoal,
)

NOW = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)


def make_goal(minutes: int = 20) -> LearningGoal:
    return LearningGoal(
        title="Complete HSK1",
        target_hsk_level=1,
        daily_available_minutes=minutes,
    )


@pytest.mark.asyncio
async def test_plan_orders_review_remedial_and_new() -> None:
    learner_id = uuid4()

    due = ConceptMastery(
        concept_id="hsk1_c01",
        mastery_score=0.80,
        retention_score=0.70,
        evidence_count=4,
        last_reviewed_at=NOW - timedelta(days=5),
        next_review_at=NOW - timedelta(days=1),
    )

    weak = ConceptMastery(
        concept_id="hsk1_c02",
        mastery_score=0.30,
        retention_score=0.90,
        evidence_count=3,
        last_reviewed_at=NOW,
        next_review_at=NOW + timedelta(days=2),
    )

    state = LearnerState(
        learner_id=learner_id,
        goal=make_goal(15),
        mastery={
            due.concept_id: due,
            weak.concept_id: weak,
        },
    )

    planner = DeterministicGoalPlanner(
        now_provider=lambda: NOW,
    )

    plan = await planner.create_plan(state)

    assert plan.learner_id == learner_id
    assert plan.status == PlanStatus.ACTIVE
    assert len(plan.items) == 3

    assert plan.items[0].concept_id == "hsk1_c01"
    assert plan.items[0].kind == PlanItemKind.REVIEW

    assert plan.items[1].concept_id == "hsk1_c02"
    assert plan.items[1].kind == PlanItemKind.REMEDIAL

    assert plan.items[2].concept_id == "hsk1_c03"
    assert plan.items[2].kind == PlanItemKind.NEW

    assert sum(item.estimated_minutes for item in plan.items) == 15


@pytest.mark.asyncio
async def test_new_learner_starts_from_first_concept() -> None:
    state = LearnerState(
        goal=make_goal(10),
    )

    planner = DeterministicGoalPlanner(
        now_provider=lambda: NOW,
    )

    plan = await planner.create_plan(state)

    assert [item.concept_id for item in plan.items] == [
        "hsk1_c01",
        "hsk1_c02",
    ]

    assert all(item.kind == PlanItemKind.NEW for item in plan.items)


@pytest.mark.asyncio
async def test_plan_does_not_exceed_available_time() -> None:
    state = LearnerState(
        goal=make_goal(7),
    )

    planner = DeterministicGoalPlanner(
        now_provider=lambda: NOW,
    )

    plan = await planner.create_plan(state)

    assert sum(item.estimated_minutes for item in plan.items) == 7

    assert plan.items[0].estimated_minutes == 5
    assert plan.items[1].estimated_minutes == 2


@pytest.mark.asyncio
async def test_due_concept_is_not_duplicated_as_remedial() -> None:
    due_and_weak = ConceptMastery(
        concept_id="hsk1_c01",
        mastery_score=0.20,
        retention_score=0.50,
        evidence_count=5,
        last_reviewed_at=NOW - timedelta(days=10),
        next_review_at=NOW - timedelta(days=1),
    )

    state = LearnerState(
        goal=make_goal(10),
        mastery={
            due_and_weak.concept_id: due_and_weak,
        },
    )

    planner = DeterministicGoalPlanner(
        now_provider=lambda: NOW,
    )

    plan = await planner.create_plan(state)

    concept_ids = [item.concept_id for item in plan.items]

    assert concept_ids.count("hsk1_c01") == 1
    assert plan.items[0].kind == PlanItemKind.REVIEW


@pytest.mark.asyncio
async def test_missing_goal_raises_error() -> None:
    state = LearnerState(goal=None)

    planner = DeterministicGoalPlanner(
        now_provider=lambda: NOW,
    )

    with pytest.raises(
        ValueError,
        match="LearningGoal is required",
    ):
        await planner.create_plan(state)


@pytest.mark.asyncio
async def test_new_concept_is_blocked_until_prerequisite_is_mastered() -> None:
    state = LearnerState(goal=make_goal(10))
    planner = DeterministicGoalPlanner(
        concept_ids=("hsk1_c01", "hsk1_c02"),
        prerequisites={"hsk1_c02": {"hsk1_c01"}},
        now_provider=lambda: NOW,
    )

    plan = await planner.create_plan(state)

    assert [item.concept_id for item in plan.items] == ["hsk1_c01"]


@pytest.mark.asyncio
async def test_mastered_prerequisite_unlocks_new_concept() -> None:
    prerequisite = ConceptMastery(
        concept_id="hsk1_c01",
        mastery_score=0.60,
        evidence_count=1,
        next_review_at=NOW + timedelta(days=1),
    )
    state = LearnerState(
        goal=make_goal(5),
        mastery={prerequisite.concept_id: prerequisite},
    )
    planner = DeterministicGoalPlanner(
        concept_ids=("hsk1_c01", "hsk1_c02"),
        prerequisites={"hsk1_c02": {"hsk1_c01"}},
        now_provider=lambda: NOW,
    )

    plan = await planner.create_plan(state)

    assert plan.items[0].concept_id == "hsk1_c02"
    assert plan.items[0].kind == PlanItemKind.NEW


@pytest.mark.asyncio
async def test_prerequisite_requires_evidence_and_threshold_mastery() -> None:
    prerequisite = ConceptMastery(
        concept_id="hsk1_c01",
        mastery_score=0.59,
        evidence_count=1,
        next_review_at=NOW + timedelta(days=1),
    )
    state = LearnerState(
        goal=make_goal(5),
        mastery={prerequisite.concept_id: prerequisite},
    )
    planner = DeterministicGoalPlanner(
        concept_ids=("hsk1_c01", "hsk1_c02"),
        prerequisites={"hsk1_c02": {"hsk1_c01"}},
        now_provider=lambda: NOW,
    )

    plan = await planner.create_plan(state)

    assert all(item.concept_id != "hsk1_c02" for item in plan.items)


def test_prerequisites_must_reference_known_curriculum_concepts() -> None:
    with pytest.raises(ValueError, match="unknown concept_ids"):
        DeterministicGoalPlanner(
            concept_ids=("hsk1_c01",),
            prerequisites={"hsk1_c02": {"hsk1_c01"}},
        )
