"""apps/api/routes/learning_loop.py
FastAPI router providing the unified closed-loop event endpoint: POST /api/v1/events.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from apps.api.dependencies import get_content_repo, get_learner_repo
from goalcoach.agents.grader_component import GraderComponent
from goalcoach.agents.planning_agent import PlanningWorker
from goalcoach.agents.teaching_agent import TeachingWorker
from goalcoach.application.orchestrator import (
    DeterministicOrchestrator,
    OrchestratorResponse,
)
from goalcoach.application.progress_service import ProgressService
from goalcoach.domain.enums import EventType
from goalcoach.infrastructure.persistence.content_service import ContentService
from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    SqliteLearnerRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["learning-loop"])


class EventRequest(BaseModel):
    """Inbound request payload for the unified event dispatcher."""

    event_type: EventType
    learner_id: UUID | str = Field(default="learner_001")
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/events", response_model=OrchestratorResponse)
async def dispatch_learning_event(
    req: EventRequest,
    learner_repo: SqliteLearnerRepository = Depends(get_learner_repo),
    content_repo: ContentRepository = Depends(get_content_repo),
) -> OrchestratorResponse:
    """Dispatches inbound learner events through the Deterministic Orchestrator."""
    content_service = ContentService(content_repo)
    progress_service = ProgressService(learner_repo=learner_repo)
    planning_worker = PlanningWorker()
    teaching_worker = TeachingWorker()
    grader_worker = GraderComponent()

    orchestrator = DeterministicOrchestrator(
        learner_repo=learner_repo,
        content_service=content_service,
        progress_service=progress_service,
        planning_worker=planning_worker,
        teaching_worker=teaching_worker,
        grader_worker=grader_worker,
    )

    return await orchestrator.handle_event(
        event_type=req.event_type,
        payload=req.payload,
        learner_id=req.learner_id,
    )
