from goalcoach.agents.grading_agent import grade_submission
from goalcoach.agents.teaching_agent import next_teaching_action
from goalcoach.agents.tools.retrieval_tools import AgentDeps
from goalcoach.domain.models import (
    AnswerSubmission,
    TeachingSession,
    TeachingTurn,
)

def evaluate_session_status(
    session: TeachingSession,
) -> str:

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
) -> TeachingSession:

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

        learner_response = input("\nYou: ")

        submission = AnswerSubmission(
            learner_id=deps.learner_state.learner_id,
            exercise_id=action.exercise.id,
            answer=learner_response,
        )

        grading_result, _ = await grade_submission(
            exercise=action.exercise,
            submission=submission,
        )

        session.turns.append(
            TeachingTurn(
                action=action,
                learner_response=learner_response,
                grading_result=grading_result,
            )
        )

        session.status = evaluate_session_status(session)

        if session.status != "active":
            break

    return session