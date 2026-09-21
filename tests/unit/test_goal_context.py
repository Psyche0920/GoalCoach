"""Tests for preserving free-form goals without categorical mapping."""

from goalcoach.domain.models import LearningGoal


def test_free_form_goal_is_preserved_without_category_mapping() -> None:
    title = "I need Mandarin for negotiating renewable-energy contracts in Chengdu"

    assert LearningGoal(title=title).title == title
