"""Typed domain event payloads and wrappers for GoalCoach event-driven orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from goalcoach.domain.enums import EventType
from goalcoach.domain.models import DomainBaseModel, utc_now


class InboundEvent(DomainBaseModel):
    """Authoritative envelope for all inbound learner interactions routed by the Orchestrator."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    event_type: EventType
    learner_id: str | UUID
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


__all__ = ["InboundEvent"]
