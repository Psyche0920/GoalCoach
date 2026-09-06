from pathlib import Path

import pytest

from goalcoach.infrastructure.persistence import ContentRepository, create_session_factory

DATABASE_PATH = Path("data/database1/goalcoach_hsk1_learning.db")


@pytest.fixture
def repository() -> ContentRepository:
    if not DATABASE_PATH.exists():
        pytest.skip("Generate Database #1 from its SQL file before running this test")
    factory = create_session_factory(f"sqlite:///{DATABASE_PATH}")
    return ContentRepository(factory)


def test_lists_seeded_concepts_in_learning_order(repository: ContentRepository) -> None:
    concepts = repository.list_concepts()

    assert len(concepts) == 20
    assert concepts[0].concept_id == "hsk1_c01"
    assert concepts[-1].concept_id == "hsk1_c20"
    assert concepts[0].vocabulary_focus == ["你好", "您好", "谢谢", "再见"]


def test_loads_teaching_cards_and_exercises(repository: ContentRepository) -> None:
    cards = repository.get_teaching_cards("hsk1_c04")
    exercises = repository.get_exercises("hsk1_c04", limit=3, randomize=False)

    assert cards[0].prompt_zh == "陈述句 + 吗？"
    assert [item.exercise_id for item in exercises] == [
        "hsk1_c04_e01",
        "hsk1_c04_e02",
        "hsk1_c04_e03",
    ]
    assert exercises[0].answer == {"value": "吗"}


def test_finds_remedial_exercises_by_exact_error_tag(
    repository: ContentRepository,
) -> None:
    exercises = repository.get_remedial_exercises("word_order", limit=5)

    assert len(exercises) == 5
    assert all("word_order" in exercise.error_tags for exercise in exercises)


def test_loads_all_prerequisite_relationships(repository: ContentRepository) -> None:
    prerequisites = repository.get_prerequisites()

    assert sum(len(required_ids) for required_ids in prerequisites.values()) == 18
    assert prerequisites["hsk1_c02"] == frozenset({"hsk1_c01"})
    assert prerequisites["hsk1_c20"] == frozenset({"hsk1_c11"})
