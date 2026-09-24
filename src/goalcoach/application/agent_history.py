"""Bounded cross-session history used as compact context by GoalCoach agents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from goalcoach.domain.models import (
    ActiveLearningSession,
    GradingResult,
    LearnerState,
    SessionSummary,
    TeachingAction,
    TeachingHistoryTurn,
    utc_now,
)

MAX_RECENT_TEACHING_TURNS = 6
MAX_SUMMARY_CHARACTERS = 240
MAX_SESSION_SUMMARIES = 30


class SessionLifecycleError(ValueError):
    """Raised when a session lifecycle event is invalid for the current state."""


@dataclass(frozen=True, slots=True)
class PendingTeachingContext:
    """Minimal operational context needed to validate one submitted answer."""

    progress_eligible: bool


def require_pending_teaching_turn(
    state: LearnerState,
    *,
    concept_id: str,
    exercise_id: str,
) -> PendingTeachingContext:
    """Ensure an answer belongs to the latest assessable Teaching Agent turn."""
    if state.active_session is None:
        raise SessionLifecycleError("Start a learning session before submitting an answer")
    session = state.active_session
    if (
        not session.current_turn_progress_eligible
        and session.pending_concept_id == concept_id
        and session.pending_exercise_id == exercise_id
    ):
        return PendingTeachingContext(progress_eligible=False)
    for turn in reversed(state.agent_history.recent_teaching_turns):
        if turn.session_id != state.active_session.session_id or turn.exercise_id is None:
            continue
        if turn.passed is not None:
            continue
        if turn.concept_id != concept_id or turn.exercise_id != exercise_id:
            raise SessionLifecycleError(
                "The submitted answer does not match the current teaching exercise"
            )
        return PendingTeachingContext(progress_eligible=turn.progress_eligible)
    raise SessionLifecycleError("No pending teaching exercise is available for this answer")


def _compact_text(value: str, limit: int = MAX_SUMMARY_CHARACTERS) -> str:
    """Collapse whitespace and bound persisted prompt context."""
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1].rstrip()}…"


def learner_local_today(state: LearnerState) -> date:
    """Return the learner's current calendar date."""
    return datetime.now(ZoneInfo(state.goal.timezone if state.goal else "UTC")).date()


def record_session_started(
    state: LearnerState,
    *,
    planned_minutes: int,
    focus: str | None = None,
) -> ActiveLearningSession:
    """Open one session, reusing an already active session idempotently."""
    today = learner_local_today(state).isoformat()
    # Only roll today's mistake/completion tracking when the recorded activity
    # date belongs to a *different prior day*. A fresh learner (None) must not
    # wipe mistakes already recorded today before the first session opens.
    if state.daily_activity_date not in (None, today):
        state.today_mistake_exercise_ids.clear()
        state.today_completed_exercise_ids.clear()
        state.today_studied_concept_ids.clear()
        state.today_remediated_concept_ids.clear()
    state.daily_activity_date = today
    if state.active_session is not None:
        started_day = state.active_session.started_at.astimezone(
            ZoneInfo(state.goal.timezone if state.goal else "UTC")
        ).date()
        if started_day.isoformat() != today:
            close_active_session(state)
    if state.active_session is not None:
        return state.active_session

    state.active_session = ActiveLearningSession(
        planned_minutes=planned_minutes,
        focus=focus,
    )
    state.agent_history.session_count += 1
    return state.active_session


def record_teaching_turn(
    state: LearnerState,
    action: TeachingAction,
    *,
    learner_query: str | None = None,
) -> None:
    """Persist a bounded summary of a Teaching Agent action."""
    exercise_id: str | None = None
    if action.exercise_payload:
        raw_exercise_id = action.exercise_payload.get("exercise_id")
        if raw_exercise_id is not None:
            exercise_id = str(raw_exercise_id)

    turn = TeachingHistoryTurn(
        concept_id=action.concept_id,
        session_id=state.active_session.session_id if state.active_session else None,
        action_kind=action.action_kind,
        exercise_id=exercise_id,
        content_summary=_compact_text(action.history_summary),
        learner_query=_compact_text(learner_query) if learner_query else None,
        entry_source=action.metadata.get("entry_source", "planned"),
        progress_eligible=bool(action.metadata.get("progress_eligible", True)),
    )
    history = state.agent_history
    history.teaching_turn_count += 1
    history.recent_teaching_turns = [
        *history.recent_teaching_turns,
        turn,
    ][-MAX_RECENT_TEACHING_TURNS:]
    if state.active_session is not None:
        session = state.active_session
        session.teaching_turn_count += 1
        session.last_activity_at = utc_now()
        if action.concept_id not in session.concepts_covered:
            session.concepts_covered.append(action.concept_id)


def record_grading_outcome(
    state: LearnerState,
    *,
    concept_id: str,
    exercise_id: str,
    result: GradingResult,
    time_spent_seconds: int = 0,
) -> None:
    """Attach grading evidence to the most recent matching teaching turn."""
    for turn in reversed(state.agent_history.recent_teaching_turns):
        if turn.concept_id == concept_id and turn.exercise_id == exercise_id:
            turn.passed = result.passed_gates
            turn.error_codes = list(dict.fromkeys(result.detected_errors))
            break

    if state.active_session is not None:
        session = state.active_session
        session.answer_count += 1
        session.passed_answer_count += int(result.passed_gates)
        session.active_seconds += time_spent_seconds
        session.last_activity_at = utc_now()
        if concept_id not in session.concepts_covered:
            session.concepts_covered.append(concept_id)


def close_active_session(
    state: LearnerState,
    *,
    additional_active_seconds: int = 0,
) -> SessionSummary:
    """Close and archive the active session using deterministic evidence."""
    session = state.active_session
    if session is None:
        raise SessionLifecycleError("No active learning session to end")

    ended_at = utc_now()
    counted_additional_seconds = (
        additional_active_seconds if session.current_turn_progress_eligible else 0
    )
    active_seconds = session.active_seconds + counted_additional_seconds
    concepts = ", ".join(session.concepts_covered) or "no concepts"
    summary = SessionSummary(
        session_id=session.session_id,
        started_at=session.started_at,
        ended_at=ended_at,
        concepts_covered=session.concepts_covered,
        planned_minutes=session.planned_minutes,
        active_seconds=active_seconds,
        teaching_turn_count=session.teaching_turn_count,
        answer_count=session.answer_count,
        passed_answer_count=session.passed_answer_count,
        summary=(
            f"Covered {concepts}; completed {session.teaching_turn_count} teaching turns and "
            f"passed {session.passed_answer_count} of {session.answer_count} answers."
        ),
    )
    if session.has_progress_eligible_activity:
        state.sessions = [*state.sessions, summary][-MAX_SESSION_SUMMARIES:]
    state.active_session = None
    state.updated_at = ended_at
    return summary


def format_agent_history(state: LearnerState) -> str:
    """Render compact, bounded history suitable for an LLM prompt."""
    history = state.agent_history
    if not history.recent_teaching_turns:
        return f"Sessions started: {history.session_count}; no prior teaching turns."

    lines = [
        (
            f"Sessions started: {history.session_count}; "
            f"total teaching turns: {history.teaching_turn_count}."
        )
    ]
    for turn in history.recent_teaching_turns:
        outcome = "not graded" if turn.passed is None else ("passed" if turn.passed else "failed")
        errors = ",".join(turn.error_codes) or "none"
        exercise = turn.exercise_id or "none"
        lines.append(
            f"- concept={turn.concept_id}; action={turn.action_kind.value}; "
            f"exercise={exercise}; outcome={outcome}; errors={errors}; "
            f"summary={turn.content_summary}"
        )
    return "\n".join(lines)
