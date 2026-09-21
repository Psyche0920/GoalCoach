"""Tests for validation of agent-authored curriculum ordering."""

from goalcoach.agents.planning_agent import validate_agent_roadmap


def test_agent_roadmap_order_is_preserved() -> None:
    concepts = ["c1", "c2", "c3"]

    ordered = validate_agent_roadmap(["c3", "c1", "c2"], concepts)

    assert ordered == ["c3", "c1", "c2"]


def test_invalid_and_duplicate_ids_are_removed_without_expanding_scope() -> None:
    concepts = ["c1", "c2", "c3"]

    assert validate_agent_roadmap(["unknown", "c2", "c2"], concepts) == ["c2"]
