"""Unit tests for deterministic progress reducer and progress summary engine."""

from datetime import UTC, datetime, timedelta

import pytest

from goalcoach.application.progress_reducer import compute_progress_summary, reduce_concept_progress
from goalcoach.domain.models import ConceptProgress, LearnerState, LearningEvent, LearningEvidence


def test_any_durable_evidence_marks_binary_exposure() -> None:
    now = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    cp = ConceptProgress(learner_id="learner_001", concept_id="c_hsk1_ma")

    event_card = LearningEvent(
        learner_id="learner_001",
        plan_item_id="item_1",
        concept_ids=["c_hsk1_ma"],
        event_type="card",
        started_at=now,
    )
    cp = reduce_concept_progress(cp, event_card)
    assert cp.exposed is True
    assert cp.learned_percent == pytest.approx(100.0)
    assert cp.status == "learning"


def test_exposure_monotonicity_guarantee() -> None:
    now = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    cp = ConceptProgress(
        learner_id="learner_001",
        concept_id="c_hsk1_ma",
        learned_percent=80.0,
        learning_evidence=LearningEvidence(card_completion=1.0, practice_completion=1.0),
    )

    # An unsuccessful attempt or low-score review event must never unmark exposure.
    event_fail = LearningEvent(
        learner_id="learner_001",
        plan_item_id="item_1",
        concept_ids=["c_hsk1_ma"],
        event_type="attempt",
        started_at=now,
        grading_result={"passed_gates": False},
        engagement_score=0.2,
    )
    reduced = reduce_concept_progress(cp, event_fail)
    assert reduced.exposed is True
    assert reduced.learned_percent == 100.0


def test_atomic_unit_completion() -> None:
    now = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    cp = ConceptProgress(learner_id="learner_001", concept_id="c_hsk1_shi")

    event = LearningEvent(
        learner_id="learner_001",
        plan_item_id="item_1",
        concept_ids=["c_hsk1_shi"],
        event_type="card",
        started_at=now,
    )
    reduced = reduce_concept_progress(cp, event, completes_atomic_unit=True)
    assert reduced.learned_percent == pytest.approx(100.0)
    assert reduced.learning_evidence.card_completion == 1.0
    assert reduced.learning_evidence.practice_completion == 1.0
    assert reduced.learning_evidence.output_completion == 1.0
    assert reduced.status == "learning"


def test_mastery_qualification_rule() -> None:
    day1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    day2 = datetime(2026, 9, 3, 10, 0, 0, tzinfo=UTC)
    day3 = datetime(2026, 9, 6, 10, 0, 0, tzinfo=UTC)
    day4 = datetime(2026, 9, 10, 10, 0, 0, tzinfo=UTC)

    cp = ConceptProgress(
        learner_id="learner_001",
        concept_id="c_hsk1_ma",
        learned_percent=100.0,
        exposed=True,
        learning_evidence=LearningEvidence(
            card_completion=1.0, practice_completion=1.0, output_completion=1.0
        ),
        status="learning",
    )

    # Retrieval 1 (Day 1)
    e1 = LearningEvent(
        learner_id="learner_001",
        plan_item_id="item_1",
        concept_ids=["c_hsk1_ma"],
        event_type="review",
        started_at=day1,
        engagement_score=0.9,
    )
    cp = reduce_concept_progress(cp, e1, is_spaced_review=True)
    assert cp.successful_spaced_retrievals == 1
    assert cp.evidence_days == 1
    assert not cp.is_mastered

    # Immediate same-day retry (Day 1): should NOT increment successful_spaced_retrievals
    e1_retry = LearningEvent(
        learner_id="learner_001",
        plan_item_id="item_1",
        concept_ids=["c_hsk1_ma"],
        event_type="review",
        started_at=day1 + timedelta(minutes=15),
        engagement_score=0.95,
    )
    cp = reduce_concept_progress(cp, e1_retry, is_spaced_review=True)
    assert cp.successful_spaced_retrievals == 1
    assert cp.evidence_days == 1
    assert not cp.is_mastered

    # Retrieval 2 (Day 2)
    e2 = LearningEvent(
        learner_id="learner_001",
        plan_item_id="item_2",
        concept_ids=["c_hsk1_ma"],
        event_type="review",
        started_at=day2,
        engagement_score=0.85,
    )
    cp = reduce_concept_progress(cp, e2, is_spaced_review=True)
    assert cp.successful_spaced_retrievals == 2
    assert cp.evidence_days == 2
    assert not cp.is_mastered

    # Retrieval 3 (Day 3)
    e3 = LearningEvent(
        learner_id="learner_001",
        plan_item_id="item_3",
        concept_ids=["c_hsk1_ma"],
        event_type="review",
        started_at=day3,
        engagement_score=0.85,
    )
    cp = reduce_concept_progress(cp, e3, is_spaced_review=True)
    assert cp.successful_spaced_retrievals == 3
    assert cp.evidence_days == 3
    assert not cp.is_mastered  # Needs >= 4 retrievals

    # Retrieval 4 (Day 4): qualifies for Mastered
    e4 = LearningEvent(
        learner_id="learner_001",
        plan_item_id="item_4",
        concept_ids=["c_hsk1_ma"],
        event_type="review",
        started_at=day4,
        engagement_score=0.9,
    )
    cp = reduce_concept_progress(cp, e4, is_spaced_review=True)
    assert cp.successful_spaced_retrievals == 4
    assert cp.evidence_days == 4
    assert cp.average_review_quality >= 0.80
    assert cp.is_mastered is True
    assert cp.status == "mastered"
    assert cp.mastery_score == 0.0


def test_exposure_retention_goal_progress_formulation() -> None:
    # Goal completion = 0.4 * exposure + 0.6 * retained mastery.
    cp1 = ConceptProgress(
        learner_id="learner_001",
        concept_id="c1",
        exposed=True,
        learned_percent=100.0,
        mastery_score=1.0,
        is_mastered=True,
        learning_evidence=LearningEvidence(output_completion=1.0),
    )
    cp2 = ConceptProgress(
        learner_id="learner_001",
        concept_id="c2",
        exposed=True,
        learned_percent=100.0,
        mastery_score=0.2,
        is_mastered=False,
    )
    state = LearnerState(
        learner_id="learner_001",
        concept_progress={"c1": cp1, "c2": cp2},
    )

    summary = compute_progress_summary(state, all_concepts=[{"id": "c1"}, {"id": "c2"}])
    assert summary.course_coverage == 100.0
    assert summary.learned_progress == 100.0
    assert summary.mastered_progress == 60.0
    assert summary.mastered_concept_rate == 50.0

    # The communication field is a compatibility projection of exposure.
    assert summary.communication_outcome_percent == 100.0

    # 0.4 * 100 + 0.6 * 60 = 76
    assert summary.goal_completion == 76.0


def test_progress_summary_counts_untracked_curriculum_as_not_learned() -> None:
    state = LearnerState(
        learner_id="learner_001",
        concept_progress={
            "c1": ConceptProgress(
                learner_id="learner_001",
                concept_id="c1",
                exposed=True,
                learned_percent=100.0,
                mastery_score=1.0,
                is_mastered=True,
            )
        },
    )

    summary = compute_progress_summary(
        state,
        all_concepts=[{"id": "c1"}, {"id": "c2"}],
    )

    assert summary.course_coverage == 50.0
    assert summary.learned_progress == 50.0
    assert summary.mastered_progress == 50.0
    assert summary.mastered_concept_rate == 50.0


def test_planned_roadmap_is_the_only_progress_scope() -> None:
    state = LearnerState(
        learner_id="goal-scope",
        roadmap_concept_ids=["c1"],
        concept_progress={
            "c1": ConceptProgress(
                learner_id="goal-scope",
                concept_id="c1",
                learned_percent=100.0,
                mastery_score=1.0,
                is_mastered=True,
                status="mastered",
                learning_evidence=LearningEvidence(
                    card_completion=1.0,
                    practice_completion=1.0,
                    output_completion=1.0,
                ),
            )
        },
    )
    summary = compute_progress_summary(
        state,
        all_concepts=[{"id": "c1"}, {"id": "c2"}],
    )
    assert summary.goal_completion == 100.0
    assert summary.learned_progress == 100.0
    assert summary.mastered_progress == 100.0
    assert summary.mastered_concept_rate == 100.0
