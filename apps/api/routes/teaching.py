"""HTTP boundary for adaptive teaching sessions."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import Field

from apps.api.dependencies import get_chroma_service, get_content_repo, get_learner_repo
from goalcoach.agents.grading_agent import PydanticAIGrader
from goalcoach.application.teaching_session_service import (
    InMemoryTeachingSessionRepository,
    InvalidTeachingStateError,
    TeachingSessionNotFoundError,
    TeachingSessionRepository,
    TeachingSessionService,
    TeachingStepResult,
)
from goalcoach.domain.models import (
    ConceptProgress,
    DomainBaseModel,
    TeachingAction,
    TeachingSession,
)
from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    SqliteLearnerRepository,
)
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService

router = APIRouter(prefix="/api/v1/teaching", tags=["teaching"])
_fallback_sessions = InMemoryTeachingSessionRepository()


class StartTeachingRequest(DomainBaseModel):
    learner_id: str = Field(min_length=1)
    concept_id: str = Field(min_length=1)


class SubmitTeachingAnswerRequest(DomainBaseModel):
    answer: str = Field(min_length=1)


class TeachingStepResponse(DomainBaseModel):
    session: TeachingSession
    action: TeachingAction | None
    progress: ConceptProgress | None


def to_response(result: TeachingStepResult) -> TeachingStepResponse:
    return TeachingStepResponse(
        session=result.session,
        action=result.action,
        progress=result.progress,
    )


def get_session_repository(request: Request) -> TeachingSessionRepository:
    if hasattr(request.app.state, "teaching_session_repository"):
        return cast(
            TeachingSessionRepository,
            request.app.state.teaching_session_repository,
        )
    return _fallback_sessions


def build_service(
    sessions: TeachingSessionRepository,
    learners: SqliteLearnerRepository,
    content: ContentRepository,
    chroma: ChromaService,
) -> TeachingSessionService:
    return TeachingSessionService(
        learner_repository=learners,
        session_repository=sessions,
        content_repository=content,
        chroma_service=chroma,
        grader=PydanticAIGrader(),
    )


@router.post("/sessions", response_model=TeachingStepResponse)
async def start_teaching_session(
    body: StartTeachingRequest,
    sessions: TeachingSessionRepository = Depends(get_session_repository),
    learners: SqliteLearnerRepository = Depends(get_learner_repo),
    content: ContentRepository = Depends(get_content_repo),
    chroma: ChromaService = Depends(get_chroma_service),
) -> TeachingStepResponse:
    result = await build_service(sessions, learners, content, chroma).start_session(
        body.learner_id,
        body.concept_id,
    )
    return to_response(result)


@router.post("/sessions/{session_id}/answers", response_model=TeachingStepResponse)
async def submit_teaching_answer(
    session_id: str,
    body: SubmitTeachingAnswerRequest,
    sessions: TeachingSessionRepository = Depends(get_session_repository),
    learners: SqliteLearnerRepository = Depends(get_learner_repo),
    content: ContentRepository = Depends(get_content_repo),
    chroma: ChromaService = Depends(get_chroma_service),
) -> TeachingStepResponse:
    try:
        result = await build_service(sessions, learners, content, chroma).submit_answer(
            session_id,
            body.answer,
        )
    except TeachingSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTeachingStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return to_response(result)


@router.post("/sessions/{session_id}/next", response_model=TeachingStepResponse)
async def advance_teaching_session(
    session_id: str,
    sessions: TeachingSessionRepository = Depends(get_session_repository),
    learners: SqliteLearnerRepository = Depends(get_learner_repo),
    content: ContentRepository = Depends(get_content_repo),
    chroma: ChromaService = Depends(get_chroma_service),
) -> TeachingStepResponse:
    try:
        result = await build_service(sessions, learners, content, chroma).next_action(
            session_id
        )
    except TeachingSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTeachingStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return to_response(result)
