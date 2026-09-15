from typing import Any, cast

import pytest

from goalcoach.agents.interfaces import GradingOutcome
from goalcoach.application.teaching_session_service import (
    InMemoryTeachingSessionRepository,
    TeachingSessionService,
)
from goalcoach.domain.models import (
    Exercise,
    GradingResult,
    LearnerState,
    RubricScores,
    TeachingAction,
)


class FakeLearnerRepository:
    def __init__(self, learner: LearnerState) -> None:
        self.learner = learner

    async def get(self, learner_id: object) -> LearnerState | None:
        return self.learner if str(learner_id) == str(self.learner.learner_id) else None

    async def save(self, state: LearnerState) -> None:
        self.learner = state


class PassingGrader:
    async def grade(self, exercise: Exercise, submission: object) -> GradingOutcome:
        return GradingOutcome(
            result=GradingResult(
                exercise_id=exercise.id,
                scores=RubricScores(
                    grammatical_correctness=1.0,
                    semantic_precision=1.0,
                    pragmatic_appropriateness=1.0,
                ),
                passed_gates=True,
                confidence=1.0,
                feedback="Correct.",
            ),
            provider="test",
        )


@pytest.mark.asyncio
async def test_answer_grades_updates_mastery_and_selects_next_action() -> None:
    learner = LearnerState(learner_id="learner-1")
    learners = FakeLearnerRepository(learner)
    sessions = InMemoryTeachingSessionRepository()
    actions = iter(
        [
            TeachingAction(
                action_type="ask",
                concept_id="hsk1_c20",
                content="请回答。",
                objective="Check ability expression.",
                expected_response=True,
                exercise=Exercise(
                    id="exercise-1",
                    concept_id="hsk1_c20",
                    prompt="请用‘会’造句。",
                    target_instruction="Use 会.",
                    reference_answers=["她会说汉语。"],
                ),
            ),
            TeachingAction(
                action_type="explain",
                concept_id="hsk1_c20",
                content="会可以表示学会的能力。",
                objective="Reinforce the concept.",
            ),
        ]
    )

    async def decide(deps: object, session: object) -> tuple[TeachingAction, str]:
        return next(actions), "test"

    service = TeachingSessionService(
        learner_repository=learners,
        session_repository=sessions,
        content_repository=cast(Any, object()),
        chroma_service=cast(Any, object()),
        grader=PassingGrader(),  # type: ignore[arg-type]
        teaching_decision=decide,  # type: ignore[arg-type]
    )

    started = await service.start_session("learner-1", "hsk1_c20")
    completed_step = await service.submit_answer(started.session.id, "她会说汉语。")

    assert completed_step.action is not None
    assert completed_step.action.action_type == "explain"
    assert completed_step.progress is not None
    assert completed_step.progress.learned_percent == 40.0
    assert completed_step.session.turns[0].grading_result is not None
