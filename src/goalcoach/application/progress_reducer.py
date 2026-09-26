"""Deterministic mathematical state reducer and progress summary engine for GoalCoach."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from goalcoach.domain.models import (
    ConceptProgress,
    DailyStudyPoint,
    LearnerState,
    LearningEvent,
    ProgressSummary,
)
from goalcoach.domain.retention import calculate_retention


def reduce_concept_progress(
    current: ConceptProgress,
    event: LearningEvent,
    completes_atomic_unit: bool = False,
    is_spaced_review: bool = False,
) -> ConceptProgress:
    """Reduce durable evidence for the Exposure/Retention/Mastery progress model.

    ``learned_percent`` is retained as an API compatibility projection and now
    means binary exposure. Scheduling mastery lives in ``ConceptMastery``; this
    reducer only tracks exposure evidence and the persistent mastery gate.
    """
    evidence_at = event.started_at or datetime.now(UTC)
    event_day = evidence_at.date()
    last_day = current.last_reviewed_at.date() if current.last_reviewed_at else None
    is_distinct_day = (last_day is None) or (last_day != event_day)

    # Any durable learning event is Exposure. ``learned_percent`` is kept for
    # existing clients and now reports 0 or 100; only Mastery can lock at true.
    exposed = True
    learned_percent = 100.0

    # 1. First-learning evidence remains useful for mastery qualification.
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

    # Almost-mastered is retained for persisted clients but is intentionally
    # never emitted by the current three-dimension model.
    if is_mastered:
        status = "mastered"
    else:
        status = "learning"

    # ConceptMastery is the sole scheduling authority. The projection field is
    # kept for API compatibility and is overwritten by ProgressService.
    mastery_score = current.mastery_score

    return current.model_copy(
        update={
            "learned_percent": max(current.learned_percent, learned_percent),
            "exposed": exposed,
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
    *,
    at: datetime | None = None,
) -> ProgressSummary:
    """Computes aggregate progress metrics across the learner's state."""
    tracked = state.concept_progress
    curriculum_ids = [
        str(getattr(concept, "concept_id", None) or concept.get("id") or concept.get("conceptId"))
        for concept in (all_concepts or [])
    ]
    roadmap_ids = (
        [
            concept_id
            for concept_id in state.roadmap_concept_ids
            if not curriculum_ids or concept_id in curriculum_ids
        ]
        or curriculum_ids
        or list(tracked)
    )
    roadmap_progress = [tracked[concept_id] for concept_id in roadmap_ids if concept_id in tracked]
    total_roadmap_count = max(len(roadmap_ids), 1)
    now = at or datetime.now(UTC)
    learner_timezone = ZoneInfo(state.goal.timezone if state.goal else "UTC")
    learner_today = now.astimezone(learner_timezone).date()

    today = learner_today
    completed_seconds = sum(
        session.active_seconds
        for session in state.sessions
        if session.ended_at.astimezone(learner_timezone).date() == today
    )
    active_seconds = state.active_session.active_seconds if state.active_session else 0
    daily_effective_minutes = round((completed_seconds + active_seconds) / 60.0, 1)
    total_effective_minutes = round(
        (sum(session.active_seconds for session in state.sessions) + active_seconds) / 60.0,
        1,
    )
    active_dates = {
        session.ended_at.astimezone(learner_timezone).date()
        for session in state.sessions
        if session.active_seconds > 0
    }
    if state.active_session and state.active_session.active_seconds > 0:
        active_dates.add(state.active_session.started_at.astimezone(learner_timezone).date())

    seconds_by_date: dict[Any, int] = {}
    check_ins_by_date: dict[Any, int] = {}
    for session in state.sessions:
        session_date = session.ended_at.astimezone(learner_timezone).date()
        seconds_by_date[session_date] = (
            seconds_by_date.get(session_date, 0) + session.active_seconds
        )
        check_ins_by_date[session_date] = check_ins_by_date.get(session_date, 0) + 1
    if state.active_session:
        active_date = state.active_session.started_at.astimezone(learner_timezone).date()
        seconds_by_date[active_date] = (
            seconds_by_date.get(active_date, 0) + state.active_session.active_seconds
        )
        check_ins_by_date.setdefault(active_date, 0)
    seconds_by_date.setdefault(today, 0)
    check_ins_by_date.setdefault(today, 0)
    daily_study_history = [
        DailyStudyPoint(
            date=study_date.isoformat(),
            effective_minutes=round(seconds / 60.0, 1),
            check_in_count=check_ins_by_date[study_date],
            timezone=state.goal.timezone if state.goal else "UTC",
        )
        for study_date, seconds in sorted(seconds_by_date.items())
    ]

    if not tracked:
        return ProgressSummary(
            state_version=state.state_version,
            course_coverage=0.0,
            learned_progress=0.0,
            mastered_progress=0.0,
            mastered_concept_rate=0.0,
            goal_completion=0.0,
            daily_effective_minutes=daily_effective_minutes,
            total_effective_minutes=total_effective_minutes,
            daily_study_history=daily_study_history,
        )

    # The established response names remain stable. Backend semantics are the
    # authoritative three dimensions: exposure, retained mastery, and mastery.
    exposed_concepts = sum(
        1 for progress in roadmap_progress if progress.exposed or progress.learned_percent > 0
    )
    exposure_rate = min(
        100.0,
        round(100.0 * (exposed_concepts / total_roadmap_count), 1),
    )
    course_coverage = exposure_rate
    learned_progress = exposure_rate

    # Effective mastery follows the PRD's honest-progress rule: mastery multiplied
    # by current retention. The scheduling projection is authoritative when present.
    effective_mastery = 0.0
    for concept_id in roadmap_ids:
        authority = state.mastery.get(concept_id)
        if authority is not None:
            effective_mastery += authority.mastery_score * authority.current_retention(now)
            continue
        projection = tracked.get(concept_id)
        if projection is None:
            continue
        retention = calculate_retention(
            retention_at_review=projection.retention_at_review,
            last_reviewed_at=projection.last_reviewed_at or now,
            at=now,
            decay_lambda=projection.decay_lambda,
        )
        effective_mastery += projection.mastery_score * retention
    retained_mastery = min(
        100.0,
        round(100.0 * effective_mastery / total_roadmap_count, 1),
    )
    mastered_progress = retained_mastery

    concepts_mastered = sum(1 for progress in roadmap_progress if progress.is_mastered)
    mastered_concept_rate = min(
        100.0,
        round(100.0 * concepts_mastered / total_roadmap_count, 1),
    )

    # Goal completion intentionally excludes the locked mastery gate: it reports
    # current knowledge (exposure) weighted against what is still retained.
    goal_completion = round(0.40 * exposure_rate + 0.60 * retained_mastery)

    return ProgressSummary(
        state_version=state.state_version,
        course_coverage=course_coverage,
        learned_progress=learned_progress,
        mastered_progress=mastered_progress,
        mastered_concept_rate=mastered_concept_rate,
        goal_completion=float(goal_completion),
        daily_effective_minutes=daily_effective_minutes,
        total_effective_minutes=total_effective_minutes,
        daily_study_history=daily_study_history,
    )
