"""Tests for validated planning configuration and application wiring."""

import pytest
from pydantic import ValidationError

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
