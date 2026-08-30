from __future__ import annotations

from typing import Protocol
from uuid import UUID

from goalcoach.domain.models import (
    AnswerSubmission,
    DailyPlan,
    Exercise,
    GradingResult,
    LearnerState,
    ProgressUpdate,
    RetrievalRequest,
)


class GoalPlanner(Protocol):
    async def create_plan(self, state: LearnerState) -> DailyPlan: ...


class Grader(Protocol):
    async def grade(self, exercise: Exercise, submission: AnswerSubmission) -> GradingResult: ...


class Teacher(Protocol):
    async def next_exercise(self, state: LearnerState) -> Exercise: ...

    async def feedback(self, exercise: Exercise, grade: GradingResult) -> str: ...


class ProgressTracker(Protocol):
    async def update(
        self, state: LearnerState, exercise: Exercise, grade: GradingResult
    ) -> ProgressUpdate: ...


class Retriever(Protocol):
    async def retrieve(self, request: RetrievalRequest) -> list[dict[str, object]]: ...


class LearnerRepository(Protocol):
    async def get(self, learner_id: UUID) -> LearnerState | None: ...

    async def save(self, state: LearnerState) -> None: ...


class ExerciseRepository(Protocol):
    async def get(self, exercise_id: UUID) -> Exercise | None: ...
