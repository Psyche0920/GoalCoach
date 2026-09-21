"""Deterministic mathematical state reducer and progress summary engine for GoalCoach."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from goalcoach.domain.models import ConceptProgress, LearnerState, LearningEvent, ProgressSummary


def reduce_concept_progress(
    current: ConceptProgress,
    event: LearningEvent,
    completes_atomic_unit: bool = False,
    is_spaced_review: bool = False,
) -> ConceptProgress:
    """Deterministically reduce concept progress following 40/40/20 and mastery gating rules.

    Rules:
    1. The 40/40/20 First-Learning Rule:
       learnedPercent = 100 * (0.40 * card + 0.40 * practice + 0.20 * output)
    2. Monotonicity: learnedPercent never decreases.
    3. Mastery Qualification Rule:
       A concept qualifies for Mastered = 100% iff:
       - successful_spaced_retrievals >= 4
       - evidence_days >= 3
       - average_review_quality >= 0.80
       (Immediate retries or multiple attempts on the same calendar day count as only 1 retrieval).
    """
    evidence_at = event.started_at or datetime.now(UTC)
    event_day = evidence_at.date()
    last_day = current.last_reviewed_at.date() if current.last_reviewed_at else None
    is_distinct_day = (last_day is None) or (last_day != event_day)

    # 1. 40/40/20 First-Learning Flow
    evidence = current.learning_evidence.model_copy()
    if completes_atomic_unit:
        evidence.card_completion = 1.0
        evidence.practice_completion = 1.0
        evidence.output_completion = 1.0
    elif not is_spaced_review and event.event_type != "review":
        if event.event_type in ("card", "audio"):
            evidence.card_completion = 1.0
        elif event.event_type == "attempt":
            passed = True
            if event.grading_result:
                passed = event.grading_result.get("passed_gates", True)
            evidence.practice_completion = max(evidence.practice_completion, 1.0 if passed else 0.5)
        elif event.event_type == "output":
            passed = True
            if event.grading_result:
                passed = event.grading_result.get("passed_gates", True)
            evidence.output_completion = max(evidence.output_completion, 1.0 if passed else 0.5)

    raw_learned = min(
        100.0,
        100.0
        * (
            0.40 * evidence.card_completion
            + 0.40 * evidence.practice_completion
            + 0.20 * evidence.output_completion
        ),
    )
    # Monotonicity: A learned concept remains learned; scores never decrease learned_percent
    learned_percent = max(current.learned_percent, raw_learned)
    evidence_days = current.evidence_days + 1 if is_distinct_day else current.evidence_days

    # 2. Spaced Retrieval Tracking & Quality
    quality = float(event.engagement_score)
    if event.grading_result:
        scores = event.grading_result.get("scores")
        if isinstance(scores, dict) and scores:
            quality = (
                float(
                    scores.get("grammatical_correctness", 1.0)
                    + scores.get("semantic_precision", 1.0)
                    + scores.get("pragmatic_appropriateness", 1.0)
                )
                / 3.0
            )

    successful_retrievals = current.successful_spaced_retrievals
    avg_review_quality = current.average_review_quality
    review_count = current.review_quality_count

    is_review_event = is_spaced_review or event.event_type == "review"
    if is_review_event:
        is_due = current.next_review_at is not None and current.next_review_at <= evidence_at
        # Count retrieval only if on a distinct calendar day or after due date
        if (is_distinct_day or is_due) and quality >= 0.75:
            successful_retrievals += 1

        avg_review_quality = ((avg_review_quality * review_count) + quality) / (review_count + 1)
        review_count += 1

    # 3. Mastery Qualification Rule: >=4 retrievals, >=3 distinct days, avg quality >= 0.80
    qualifies_mastery = (
        successful_retrievals >= 4 and evidence_days >= 3 and avg_review_quality >= 0.80
    )
    is_mastered = current.is_mastered or qualifies_mastery

    interval = max(1.0, float(successful_retrievals * 2.0))
    next_review = evidence_at + timedelta(days=interval)

    if is_mastered:
        status = "mastered"
    elif learned_percent >= 100.0:
        status = "almost_mastered"
    elif learned_percent > 0.0:
        status = "learning"
    else:
        status = "not_started"

    if is_mastered:
        mastery_score = 1.0
    elif is_review_event:
        mastery_score = min(1.0, current.mastery_score + 0.25)
    else:
        mastery_score = min(0.35, (learned_percent / 100.0) * 0.35)

    return current.model_copy(
        update={
            "learned_percent": learned_percent,
            "learning_evidence": evidence,
            "evidence_days": evidence_days,
            "successful_spaced_retrievals": successful_retrievals,
            "review_quality_count": review_count,
            "average_review_quality": avg_review_quality,
            "is_mastered": is_mastered,
            "status": status,
            "mastery_score": mastery_score,
            "last_reviewed_at": evidence_at,
            "next_review_at": next_review,
        }
    )


def compute_progress_summary(
    state: LearnerState,
    all_concepts: list[Any] | None = None,
) -> ProgressSummary:
    """Computes aggregate progress metrics across the learner's state."""
    tracked = state.concept_progress
    curriculum_ids = [
        str(getattr(concept, "concept_id", None) or concept.get("id") or concept.get("conceptId"))
        for concept in (all_concepts or [])
    ]
    scope_ids = [
        concept_id
        for concept_id in state.roadmap_concept_ids
        if not curriculum_ids or concept_id in curriculum_ids
    ] or curriculum_ids or list(tracked)
    scoped_progress = [tracked[concept_id] for concept_id in scope_ids if concept_id in tracked]
    total_scope_count = max(len(scope_ids), 1)

    today = datetime.now(UTC).date()
    completed_seconds = sum(
        session.active_seconds for session in state.sessions if session.ended_at.date() == today
    )
    active_seconds = state.active_session.active_seconds if state.active_session else 0
    daily_effective_minutes = round((completed_seconds + active_seconds) / 60.0, 1)
    total_effective_minutes = round(
        (sum(session.active_seconds for session in state.sessions) + active_seconds) / 60.0,
        1,
    )
    active_dates = {
        session.ended_at.date() for session in state.sessions if session.active_seconds > 0
    }
    if state.active_session and state.active_session.active_seconds > 0:
        active_dates.add(state.active_session.started_at.date())

    if not tracked:
        return ProgressSummary(
            state_version=state.state_version,
            course_coverage=0.0,
            learned_progress=0.0,
            mastered_progress=0.0,
            goal_completion=0.0,
            goal_scope_learned_percent=0.0,
            goal_scope_mastered_percent=0.0,
            communication_outcome_percent=0.0,
            daily_effective_minutes=daily_effective_minutes,
            total_effective_minutes=total_effective_minutes,
            active_days=len(active_dates),
        )

    # 1. Course Coverage & Progress
    concepts_started = sum(1 for p in scoped_progress if p.learned_percent > 0)
    course_coverage = min(100.0, round(100.0 * (concepts_started / total_scope_count), 1))

    total_learned = sum(p.learned_percent for p in scoped_progress)
    learned_progress = min(100.0, round(total_learned / total_scope_count, 1))

    concepts_mastered = sum(1 for p in scoped_progress if p.is_mastered)
    mastered_progress = min(
        100.0, round(100.0 * (concepts_mastered / total_scope_count), 1)
    )

    # 2. Goal Scope Progress
    goal_scope_learned_percent = learned_progress
    total_mastery = sum(p.mastery_score for p in scoped_progress)
    goal_scope_mastered_percent = min(
        100.0, round(100.0 * (total_mastery / total_scope_count), 1)
    )

    # Communication outcomes are represented by successful assessed output evidence.
    communication_outcome_percent = min(
        100.0,
        round(
            sum(p.learning_evidence.output_completion * 100.0 for p in scoped_progress)
            / total_scope_count,
            1,
        ),
    )

    # Goal completion combines coverage, durable mastery, and communicative output.
    goal_completion = round(
        0.45 * goal_scope_learned_percent
        + 0.35 * goal_scope_mastered_percent
        + 0.20 * communication_outcome_percent
    )

    return ProgressSummary(
        state_version=state.state_version,
        course_coverage=course_coverage,
        learned_progress=learned_progress,
        mastered_progress=mastered_progress,
        goal_completion=float(goal_completion),
        goal_scope_learned_percent=goal_scope_learned_percent,
        goal_scope_mastered_percent=goal_scope_mastered_percent,
        communication_outcome_percent=communication_outcome_percent,
        daily_effective_minutes=daily_effective_minutes,
        total_effective_minutes=total_effective_minutes,
        active_days=len(active_dates),
    )
