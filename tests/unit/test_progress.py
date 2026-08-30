import pytest

from goalcoach.domain.models import ConceptMastery, LearnerState


def test_progress_combines_mastery_retention_and_weight() -> None:
    state = LearnerState(
        mastery={
            "a": ConceptMastery(concept_id="a", mastery=1.0, retention=0.5, weight=1),
            "b": ConceptMastery(concept_id="b", mastery=0.5, retention=1.0, weight=3),
        }
    )
    assert state.overall_progress() == pytest.approx(0.5)
