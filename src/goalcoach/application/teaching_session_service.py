"""Application service for multi-request adaptive teaching sessions."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from goalcoach.agents.interfaces import Grader, LearnerRepository
from goalcoach.agents.teaching_agent import next_teaching_action
from goalcoach.agents.tools.retrieval_tools import AgentDeps
from goalcoach.application.teaching_loop import (
    evaluate_session_status,
    update_mastery_from_grade,
)
from goalcoach.domain.models import (
    AnswerSubmission,
    ConceptProgress,
    LearnerState,
    LearningEvent,
    TeachingAction,
    TeachingSession,
    TeachingTurn,
    utc_now,
)
from goalcoach.infrastructure.persistence.repositories import ContentRepository
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService


class TeachingSessionNotFoundError(LookupError):
    """Raised when a requested teaching session does not exist."""


class InvalidTeachingStateError(RuntimeError):
    """Raised when an answer does not match the session's pending action."""


class TeachingSessionRepository(Protocol):
    async def get(self, session_id: UUID | str) -> TeachingSession | None: ...
    async def save(self, session: TeachingSession) -> None: ...


@runtime_checkable
class TeachingTransitionRepository(Protocol):
    """Atomic persistence boundary for one completed teaching attempt."""

    async def save_transition(
        self,
        learner: LearnerState,
        event: LearningEvent,
        session: TeachingSession,
    ) -> None: ...


class InMemoryTeachingSessionRepository:
    """Concurrency-safe session store suitable for one API process."""

    def __init__(self) -> None:
        self._sessions: dict[str, TeachingSession] = {}
        self._lock = asyncio.Lock()

    async def get(self, session_id: UUID | str) -> TeachingSession | None:
        async with self._lock:
            session = self._sessions.get(str(session_id))
            return session.model_copy(deep=True) if session else None

    async def save(self, session: TeachingSession) -> None:
        async with self._lock:
            self._sessions[str(session.id)] = session.model_copy(deep=True)


@dataclass(frozen=True, slots=True)
class TeachingStepResult:
    session: TeachingSession
    action: TeachingAction | None
    progress: ConceptProgress | None


TeachingDecision = Callable[
    [AgentDeps, TeachingSession], Awaitable[tuple[TeachingAction, str]]
]


class TeachingSessionService:
    """Coordinate teaching decisions, grading, progression, and persistence."""

    def __init__(
        self,
        learner_repository: LearnerRepository,
        session_repository: TeachingSessionRepository,
        content_repository: ContentRepository,
        chroma_service: ChromaService,
        grader: Grader,
        teaching_decision: TeachingDecision = next_teaching_action,
    ) -> None:
        self._learners = learner_repository
        self._sessions = session_repository
        self._content = content_repository
        self._chroma = chroma_service
        self._grader = grader
        self._teaching_decision = teaching_decision

    async def start_session(self, learner_id: UUID | str, concept_id: str) -> TeachingStepResult:
        learner = await self._learners.get(learner_id)
        if learner is None:
            learner = LearnerState(learner_id=learner_id)
            await self._learners.save(learner)
        session = TeachingSession(learner_id=learner_id, concept_id=concept_id)
        action = await self._advance(learner, session)
        await self._sessions.save(session)
        return self._result(learner, session, action)

    async def submit_answer(self, session_id: UUID | str, answer: str) -> TeachingStepResult:
        clean_answer = answer.strip()
        if not clean_answer:
            raise ValueError("Answer cannot be empty.")
        session = await self._sessions.get(session_id)
        if session is None:
            raise TeachingSessionNotFoundError(str(session_id))
        learner = await self._learners.get(session.learner_id)
        if learner is None:
            raise TeachingSessionNotFoundError(f"Learner {session.learner_id}")
        action = session.pending_action
        if action is None or not action.expected_response or action.exercise is None:
            raise InvalidTeachingStateError("Session has no exercise awaiting an answer.")

        submission = AnswerSubmission(
            learner_id=learner.learner_id,
            exercise_id=action.exercise.id,
            answer=clean_answer,
        )
        outcome = await self._grader.grade(action.exercise, submission)
        session.turns.append(TeachingTurn(
            action=action,
            learner_response=clean_answer,
            grading_result=outcome.result,
        ))
        session.pending_action = None
        deps = self._deps(learner)
        event = update_mastery_from_grade(
            deps,
            session,
            str(action.exercise.id),
            outcome.result,
        )
        session.status = evaluate_session_status(session)
        next_action = await self._advance(learner, session) if session.status == "active" else None
        session.updated_at = utc_now()
        if isinstance(self._sessions, TeachingTransitionRepository):
            await self._sessions.save_transition(learner, event, session)
        else:
            await self._learners.save(learner)
            await self._sessions.save(session)
        return self._result(learner, session, next_action)

    async def next_action(self, session_id: UUID | str) -> TeachingStepResult:
        """Advance after a non-interactive explain, hint, or remediation action."""
        session = await self._sessions.get(session_id)
        if session is None:
            raise TeachingSessionNotFoundError(str(session_id))
        if session.status != "active":
            raise InvalidTeachingStateError("Teaching session has already ended.")
        if session.pending_action is not None:
            raise InvalidTeachingStateError("The pending exercise requires an answer.")
        learner = await self._learners.get(session.learner_id)
        if learner is None:
            raise TeachingSessionNotFoundError(f"Learner {session.learner_id}")
        action = await self._advance(learner, session)
        await self._sessions.save(session)
        return self._result(learner, session, action)

    async def _advance(self, learner: LearnerState, session: TeachingSession) -> TeachingAction:
        action, _ = await self._teaching_decision(self._deps(learner), session)
        if action.expected_response:
            if action.exercise is None:
                raise InvalidTeachingStateError("Response action has no exercise.")
            session.pending_action = action
        else:
            session.turns.append(TeachingTurn(action=action))
        session.updated_at = utc_now()
        return action

    def _deps(self, learner: LearnerState) -> AgentDeps:
        return AgentDeps(learner, self._content, self._chroma)

    @staticmethod
    def _result(
        learner: LearnerState,
        session: TeachingSession,
        action: TeachingAction | None,
    ) -> TeachingStepResult:
        return TeachingStepResult(
            session=session,
            action=action,
            progress=learner.concept_progress.get(session.concept_id),
        )
