"""apps/api/routes/tutoring.py
FastAPI route providing the interactive tutoring chat endpoint.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.api.dependencies import get_chroma_service, get_content_repo, get_learner_repo
from goalcoach.agents.teaching_agent import TutorResponse, chat_with_tutor
from goalcoach.agents.tools.retrieval_tools import AgentDeps
from goalcoach.domain.models import LearnerState, LearningGoal
from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    SqliteLearnerRepository,
)
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService

router = APIRouter(tags=["tutoring"])


class ChatRequest(BaseModel):
    learner_id: UUID | str = "learner_001"
    message: str | None = None
    messages: list[dict[str, Any]] | None = None
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    response: TutorResponse
    reply: str
    provider: str


async def handle_tutoring_chat(
    req: ChatRequest,
    learner_repo: SqliteLearnerRepository,
    content_repo: ContentRepository,
    chroma_service: ChromaService,
) -> ChatResponse:
    # Extract user message from either single message or messages array
    user_message = req.message
    if not user_message and req.messages:
        for m in reversed(req.messages):
            if m.get("role") == "user" and m.get("content"):
                user_message = m["content"]
                break
    if not user_message:
        user_message = "Hello Coach Baobao!"

    str_learner_id = str(req.learner_id)
    state = await learner_repo.get(str_learner_id)
    if not state:
        state = LearnerState(
            learner_id=str_learner_id,
            display_name="Learner",
            goal=LearningGoal(title="HSK1 Mastery", target_hsk_level=1),
        )
        await learner_repo.save(state)

    deps = AgentDeps(
        learner_state=state,
        content_repo=content_repo,
        chroma_service=chroma_service,
    )
    tutor_reply, provider = await chat_with_tutor(deps, user_message)
    return ChatResponse(
        response=tutor_reply,
        reply=tutor_reply.reply,
        provider=provider,
    )


@router.post("/tutoring/chat", response_model=ChatResponse)
async def tutoring_chat_endpoint(
    req: ChatRequest,
    learner_repo: SqliteLearnerRepository = Depends(get_learner_repo),
    content_repo: ContentRepository = Depends(get_content_repo),
    chroma_service: ChromaService = Depends(get_chroma_service),
) -> ChatResponse:
    """Chat with the adaptive bilingual Chinese tutor agent."""
    return await handle_tutoring_chat(req, learner_repo, content_repo, chroma_service)


@router.post("/chat", response_model=ChatResponse)
async def legacy_chat_endpoint(
    req: ChatRequest,
    learner_repo: SqliteLearnerRepository = Depends(get_learner_repo),
    content_repo: ContentRepository = Depends(get_content_repo),
    chroma_service: ChromaService = Depends(get_chroma_service),
) -> ChatResponse:
    """Backwards compatibility alias for /api/v1/chat."""
    return await handle_tutoring_chat(req, learner_repo, content_repo, chroma_service)
