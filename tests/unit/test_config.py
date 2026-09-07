"""Tests for validated planning configuration and application wiring."""

import pytest
from pydantic import ValidationError

from apps.api.main import create_goal_planner
from goalcoach.domain.models import LearnerState, LearningGoal
from goalcoach.infrastructure.config import Settings


def test_planning_item_minutes_defaults_to_five(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOALCOACH_PLANNING_ITEM_MINUTES", raising=False)
    settings = Settings(_env_file=None)

    assert settings.planning_item_minutes == 5


def test_planning_item_minutes_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOALCOACH_PLANNING_ITEM_MINUTES", "12")

    settings = Settings(_env_file=None)

    assert settings.planning_item_minutes == 12


@pytest.mark.parametrize("invalid_minutes", [0, -1, 121])
def test_planning_item_minutes_rejects_invalid_values(invalid_minutes: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, planning_item_minutes=invalid_minutes)


@pytest.mark.asyncio
async def test_configured_item_minutes_are_injected_into_planner() -> None:
    settings = Settings(_env_file=None, planning_item_minutes=8)
    planner = create_goal_planner(settings, prerequisites={})
    state = LearnerState(
        goal=LearningGoal(
            title="Complete HSK 1",
            target_hsk_level=1,
            daily_available_minutes=25,
        )
    )

    plan = await planner.create_plan(state)

    assert [item.estimated_minutes for item in plan.items] == [8, 8, 8, 1]
