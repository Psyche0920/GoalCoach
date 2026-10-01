"""Compose configured decision providers without changing orchestrator contracts."""

from __future__ import annotations

from goalcoach.agents.jev_planning import JevPlanningWorker
from goalcoach.agents.jev_teaching import JevTeachingWorker
from goalcoach.agents.planning_agent import PlanningWorker
from goalcoach.agents.teaching_agent import TeachingWorker
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.llm.jev_client import JevClient


def create_planning_worker() -> PlanningWorker | JevPlanningWorker:
    settings = Settings()
    fallback = PlanningWorker()
    return (
        JevPlanningWorker(JevClient(settings), fallback)
        if settings.jev_enabled
        else fallback
    )


def create_teaching_worker() -> TeachingWorker | JevTeachingWorker:
    settings = Settings()
    fallback = TeachingWorker()
    return (
        JevTeachingWorker(JevClient(settings), fallback)
        if settings.jev_enabled
        else fallback
    )
