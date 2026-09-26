"""Focused tests for bounded cross-session agent history."""

import pytest

from goalcoach.application.agent_history import (
    MAX_RECENT_TEACHING_TURNS,
    SessionLifecycleError,
    close_active_session,
    format_agent_history,
    record_grading_outcome,
    record_session_started,
    record_teaching_turn,
)
from goalcoach.domain.enums import TeachingActionKind
from goalcoach.domain.models import GradingResult, LearnerState, RubricScores, TeachingAction


def _action(index: int) -> TeachingAction:
    return TeachingAction(
        action_kind=TeachingActionKind.EXERCISE,
        concept_id=f"concept-{index}",
        content=f"Teaching content {index} " + ("x" * 300),
        history_summary=f"Practised concept {index} with a targeted exercise.",
        exercise_payload={"exercise_id": f"exercise-{index}"},
    )


def test_history_is_persisted_as_a_bounded_summary() -> None:
    state = LearnerState()
    session = record_session_started(state, planned_minutes=20, focus="Travel Chinese")

    for index in range(MAX_RECENT_TEACHING_TURNS + 2):
        record_teaching_turn(state, _action(index))

    history = state.agent_history
    assert history.session_count == 1
    assert state.active_session is not None
    assert state.active_session.session_id == session.session_id
    assert history.teaching_turn_count == MAX_RECENT_TEACHING_TURNS + 2
    assert len(history.recent_teaching_turns) == MAX_RECENT_TEACHING_TURNS
    assert history.recent_teaching_turns[0].concept_id == "concept-2"
    assert history.recent_teaching_turns[-1].content_summary == (
        f"Practised concept {MAX_RECENT_TEACHING_TURNS + 1} with a targeted exercise."
    )

    restored = LearnerState.model_validate_json(state.model_dump_json())
    assert restored.agent_history == history


def test_session_lifecycle_accumulates_and_archives_bounded_evidence() -> None:
    state = LearnerState()
    first = record_session_started(state, planned_minutes=15)
    repeated = record_session_started(state, planned_minutes=30)
    assert repeated.session_id == first.session_id
    assert state.agent_history.session_count == 1

    record_teaching_turn(state, _action(1))
    result = GradingResult(
        exercise_id="exercise-1",
        scores=RubricScores(
            grammatical_correctness=1.0,
            semantic_precision=1.0,
            pragmatic_appropriateness=1.0,
        ),
        passed_gates=True,
        confidence=1.0,
        feedback="Correct.",
    )
    record_grading_outcome(
        state,
        concept_id="concept-1",
        exercise_id="exercise-1",
        result=result,
        time_spent_seconds=45,
    )
    summary = close_active_session(state, additional_active_seconds=15)

    assert state.active_session is None
    assert summary.active_seconds == 60
    assert summary.teaching_turn_count == 1
    assert summary.answer_count == 1
    assert summary.passed_answer_count == 1
    assert summary.concepts_covered == ["concept-1"]
    assert state.sessions[-1] == summary

    with pytest.raises(SessionLifecycleError):
        close_active_session(state)


def test_grading_outcome_updates_latest_matching_turn() -> None:
    state = LearnerState()
    action = _action(1)
    record_teaching_turn(state, action)
    record_grading_outcome(
        state,
        concept_id="concept-1",
        exercise_id="exercise-1",
        result=GradingResult(
            exercise_id="exercise-1",
            scores=RubricScores(
                grammatical_correctness=0.4,
                semantic_precision=0.5,
                pragmatic_appropriateness=0.5,
            ),
            passed_gates=False,
            confidence=0.9,
            feedback="Review the word order.",
            detected_errors=["word_order", "word_order"],
        ),
    )

    turn = state.agent_history.recent_teaching_turns[-1]
    assert turn.passed is False
    assert turn.error_codes == ["word_order"]
    prompt_context = format_agent_history(state)
    assert "outcome=failed" in prompt_context
    assert "errors=word_order" in prompt_context
