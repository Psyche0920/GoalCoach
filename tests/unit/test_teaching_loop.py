from types import SimpleNamespace
from typing import cast

import pytest

from goalcoach.agents.grading_agent import PydanticAIGrader
from goalcoach.agents.tools.retrieval_tools import AgentDeps
from goalcoach.application.teaching_loop import update_mastery_from_grade
from goalcoach.domain.models import (
    AnswerSubmission,
    Exercise,
    GradingResult,
    LearnerState,
    RubricScores,
    TeachingSession,
)


@pytest.mark.asyncio
async def test_grader_uses_deterministic_path_for_reference_answer() -> None:
    exercise = Exercise(
        id="exercise-1",
        concept_id="hsk1_c20",
        prompt="请用‘会’造句。",
        target_instruction="Use 会 to describe an ability.",
        reference_answers=["她会说汉语。"],
    )
    submission = AnswerSubmission(
        learner_id="learner-1",
        exercise_id=exercise.id,
        answer="她会说汉语。",
    )

    outcome = await PydanticAIGrader().grade(exercise, submission)

    assert outcome.result.passed_gates is True
    assert outcome.provider == "deterministic:rule_match"


def test_grade_updates_current_concept_mastery() -> None:
    learner_state = LearnerState(learner_id="learner-1")
    deps = cast(AgentDeps, SimpleNamespace(learner_state=learner_state))
    session = TeachingSession(learner_id="learner-1", concept_id="hsk1_c20")
    grading_result = GradingResult(
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

    update_mastery_from_grade(
        deps=deps,
        session=session,
        exercise_id="exercise-1",
        grading_result=grading_result,
    )

    progress = learner_state.concept_progress[session.concept_id]
    assert progress.learned_percent == 40.0
    assert progress.learning_evidence.practice_completion == 1.0
    assert learner_state.state_version == 2
