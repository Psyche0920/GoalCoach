"""
apps/api/routes/tutoring.py
FastAPI route providing the interactive tutoring chat endpoint.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from apps.api.dependencies import get_chroma_service, get_content_repo, get_learner_repo
from goalcoach.agents.teaching_agent import TutorResponse, chat_with_tutor
from goalcoach.agents.tools.retrieval_tools import AgentDeps
from goalcoach.domain.models import LearnerState, LearningGoal
from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    SqliteLearnerRepository,
)
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService

router = APIRouter(prefix="/tutoring", tags=["tutoring"])


class ChatRequest(BaseModel):
    learner_id: UUID
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    response: TutorResponse
    provider: str


@router.post("/chat", response_model=ChatResponse)
async def tutoring_chat_endpoint(
    req: ChatRequest,
    learner_repo: SqliteLearnerRepository = Depends(get_learner_repo),
    content_repo: ContentRepository = Depends(get_content_repo),
    chroma_service: ChromaService = Depends(get_chroma_service),
) -> ChatResponse:
    """Chat with the adaptive bilingual Chinese tutor agent."""
    state = await learner_repo.get(req.learner_id)
    if not state:
        state = LearnerState(
            learner_id=req.learner_id,
            goal=LearningGoal(title="HSK1 Mastery", target_hsk_level=1),
        )
        await learner_repo.save(state)

    deps = AgentDeps(
        learner_state=state,
        content_repo=content_repo,
        chroma_service=chroma_service,
    )
    tutor_reply, provider = await chat_with_tutor(deps, req.message)
    return ChatResponse(response=tutor_reply, provider=provider)
