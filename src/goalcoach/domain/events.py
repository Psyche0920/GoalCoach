"""Typed domain event payloads and wrappers for GoalCoach event-driven orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from goalcoach.domain.enums import EventType
from goalcoach.domain.models import DomainBaseModel, utc_now


class GoalCreatedPayload(DomainBaseModel):
    """Payload provided when a learner creates or updates a curriculum goal."""

    title: str = Field(default="HSK 1 Complete Goal", min_length=1, max_length=255)
    target_hsk_level: int = Field(default=1, ge=1, le=6)
    daily_available_minutes: int = Field(default=20, gt=0, le=240)


class SessionStartedPayload(DomainBaseModel):
    """Payload provided when a learner starts a daily study session."""

    preferred_duration_minutes: int | None = Field(default=None, gt=0, le=240)
    session_focus: str | None = None


class SessionEndedPayload(DomainBaseModel):
    """Payload provided when the learner explicitly closes a study session."""

    additional_active_seconds: int = Field(default=0, ge=0, le=86400)


class HelpRequestedPayload(DomainBaseModel):
    """Payload provided when a learner explicitly signals confusion or asks for coach guidance."""

    concept_id: str = Field(min_length=1, max_length=128)
    current_exercise_id: str | None = None
    learner_query: str | None = None
    previous_response: str | None = None


class AnswerSubmittedPayload(DomainBaseModel):
    """Payload provided when a learner submits an answer to a practice exercise."""

    exercise_id: str = Field(min_length=1, max_length=128)
    concept_id: str = Field(min_length=1, max_length=128)
    answer: str = Field(min_length=1)
    time_spent_seconds: int = Field(default=30, ge=0)


class InboundEvent(DomainBaseModel):
    """Authoritative envelope for all inbound learner interactions routed by the Orchestrator."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    event_type: EventType
    learner_id: str | UUID
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


__all__ = [
    "AnswerSubmittedPayload",
    "GoalCreatedPayload",
    "HelpRequestedPayload",
    "InboundEvent",
    "SessionEndedPayload",
    "SessionStartedPayload",
]
