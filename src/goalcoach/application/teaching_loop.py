from goalcoach.agents.grading_agent import PydanticAIGrader
from goalcoach.agents.interfaces import Grader
from goalcoach.agents.teaching_agent import next_teaching_action
from goalcoach.agents.tools.retrieval_tools import AgentDeps
from goalcoach.application.progress_reducer import reduce_concept_progress
from goalcoach.domain.models import (
    AnswerSubmission,
    ConceptProgress,
    GradingResult,
    LearningEvent,
    TeachingSession,
    TeachingSessionStatus,
    TeachingTurn,
    utc_now,
)


def update_mastery_from_grade(
    deps: AgentDeps,
    session: TeachingSession,
    exercise_id: str,
    grading_result: GradingResult,
) -> LearningEvent:
    """Apply grading evidence to the learner aggregate deterministically."""
    learner_id = str(deps.learner_state.learner_id)
    current = deps.learner_state.concept_progress.get(
        session.concept_id,
        ConceptProgress(
            learner_id=learner_id,
            concept_id=session.concept_id,
        ),
    )
    event = LearningEvent(
        learner_id=learner_id,
        plan_item_id=exercise_id,
        concept_ids=[session.concept_id],
        event_type="attempt",
        grading_result=grading_result.model_dump(),
    )
    deps.learner_state.concept_progress[session.concept_id] = (
        reduce_concept_progress(current, event)
    )
    deps.learner_state.state_version += 1
    deps.learner_state.updated_at = utc_now()
    return event


def evaluate_session_status(
    session: TeachingSession,
) -> TeachingSessionStatus:

    graded_turns = [
        turn
        for turn in session.turns
        if turn.grading_result is not None
    ]

    # Completion: latest 2 graded attempts both passed
    if len(graded_turns) >= 2:
        last_two = graded_turns[-2:]

        if all(
            turn.grading_result.passed_gates
            for turn in last_two
        ):
            return "completed"

    # Safety limit: stop after 6 graded attempts
    if len(graded_turns) >= 6:
        return "attempt_limit_reached"

    return "active"


async def run_teaching_session(
    deps: AgentDeps,
    session: TeachingSession,
    grader: Grader | None = None,
) -> TeachingSession:

    grading_service = grader or PydanticAIGrader()

    while True:

        action, _ = await next_teaching_action(
            deps=deps,
            session=session,
        )

        print(f"\n[{action.action_type.upper()}]")
        print(action.content)

        if not action.expected_response:
            session.turns.append(TeachingTurn(action=action))
            continue

        if action.exercise is None:
            raise ValueError(
                "TeachingAction requiring a response must contain an Exercise."
            )

        print(action.exercise.prompt)

        while True:
            learner_response = input("\nYou: ").strip()

            if learner_response:
                break

            print("回答不能为空，请重新输入。")

        submission = AnswerSubmission(
            learner_id=deps.learner_state.learner_id,
            exercise_id=action.exercise.id,
            answer=learner_response,
        )

        grading_outcome = await grading_service.grade(
            exercise=action.exercise,
            submission=submission,
        )
        grading_result = grading_outcome.result

        session.turns.append(
            TeachingTurn(
                action=action,
                learner_response=learner_response,
                grading_result=grading_result,
            )
        )

        update_mastery_from_grade(
            deps=deps,
            session=session,
            exercise_id=str(action.exercise.id),
            grading_result=grading_result,
        )

        session.status = evaluate_session_status(session)

        if session.status != "active":
            break

    return session
