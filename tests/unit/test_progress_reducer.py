"""Unit tests for deterministic progress reducer and progress summary engine."""

from datetime import UTC, datetime, timedelta

import pytest

from goalcoach.application.progress_reducer import compute_progress_summary, reduce_concept_progress
from goalcoach.domain.models import ConceptProgress, LearnerState, LearningEvent, LearningEvidence


def test_40_40_20_first_learning_rule() -> None:
    now = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    cp = ConceptProgress(learner_id="learner_001", concept_id="c_hsk1_ma")

    # Step 1: Card completion gives 40%
    event_card = LearningEvent(
        learner_id="learner_001",
        plan_item_id="item_1",
        concept_ids=["c_hsk1_ma"],
        event_type="card",
        started_at=now,
    )
    cp = reduce_concept_progress(cp, event_card)
    assert cp.learned_percent == pytest.approx(40.0)
    assert cp.status == "learning"

    # Step 2: Practice attempt gives +40% (total 80%)
    event_practice = LearningEvent(
        learner_id="learner_001",
        plan_item_id="item_1",
        concept_ids=["c_hsk1_ma"],
        event_type="attempt",
        started_at=now,
        grading_result={"passed_gates": True},
    )
    cp = reduce_concept_progress(cp, event_practice)
    assert cp.learned_percent == pytest.approx(80.0)
    assert cp.status == "learning"

    # Step 3: Output submission gives +20% (total 100%)
    event_output = LearningEvent(
        learner_id="learner_001",
        plan_item_id="item_1",
        concept_ids=["c_hsk1_ma"],
        event_type="output",
        started_at=now,
        grading_result={"passed_gates": True},
    )
    cp = reduce_concept_progress(cp, event_output)
    assert cp.learned_percent == pytest.approx(100.0)
    assert cp.status == "almost_mastered"


def test_monotonicity_guarantee() -> None:
    now = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    cp = ConceptProgress(
        learner_id="learner_001",
        concept_id="c_hsk1_ma",
        learned_percent=80.0,
        learning_evidence=LearningEvidence(card_completion=1.0, practice_completion=1.0),
    )

    # An unsuccessful attempt or low-score review event must NEVER reduce learned_percent
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
    assert reduced.learned_percent == 80.0


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
    assert reduced.status == "almost_mastered"


def test_mastery_qualification_rule() -> None:
    day1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    day2 = datetime(2026, 9, 3, 10, 0, 0, tzinfo=UTC)
    day3 = datetime(2026, 9, 6, 10, 0, 0, tzinfo=UTC)
    day4 = datetime(2026, 9, 10, 10, 0, 0, tzinfo=UTC)

    cp = ConceptProgress(
        learner_id="learner_001",
        concept_id="c_hsk1_ma",
        learned_percent=100.0,
        learning_evidence=LearningEvidence(
            card_completion=1.0, practice_completion=1.0, output_completion=1.0
        ),
        status="almost_mastered",
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
    assert cp.mastery_score == 1.0


def test_composite_goal_progress_formulation() -> None:
    # 0.45 * Learned + 0.35 * Mastered + 0.20 * Communication
    cp1 = ConceptProgress(
        learner_id="learner_001",
        concept_id="c1",
        learned_percent=100.0,
        mastery_score=1.0,
        is_mastered=True,
        learning_evidence=LearningEvidence(output_completion=1.0),
    )
    cp2 = ConceptProgress(
        learner_id="learner_001",
        concept_id="c2",
        learned_percent=60.0,
        mastery_score=0.2,
        is_mastered=False,
    )
    state = LearnerState(
        learner_id="learner_001",
        concept_progress={"c1": cp1, "c2": cp2},
    )

    summary = compute_progress_summary(state, all_concepts=[{"id": "c1"}, {"id": "c2"}])
    assert summary.course_coverage == 100.0
    assert summary.learned_progress == 80.0
    assert summary.mastered_progress == 50.0

    # One of two roadmap concepts has assessed output evidence.
    assert summary.communication_outcome_percent == 50.0

    # 0.45 * 80 + 0.35 * 60 + 0.20 * 50 = 36 + 21 + 10 = 67
    assert summary.goal_completion == 67.0


def test_progress_summary_counts_untracked_curriculum_as_not_learned() -> None:
    state = LearnerState(
        learner_id="learner_001",
        concept_progress={
            "c1": ConceptProgress(
                learner_id="learner_001",
                concept_id="c1",
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
    assert summary.goal_scope_mastered_percent == 50.0
