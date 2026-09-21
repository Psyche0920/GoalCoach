"""Domain enumerations for learning plan items, plan execution statuses, events, and pedagogical actions."""

from enum import StrEnum


class EventType(StrEnum):
    """Classification of inbound learner events processed by the deterministic orchestrator."""

    GOAL_CREATED = "GOAL_CREATED"
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_ENDED = "SESSION_ENDED"
    HELP_REQUESTED = "HELP_REQUESTED"
    ANSWER_SUBMITTED = "ANSWER_SUBMITTED"


class TeachingActionKind(StrEnum):
    """Pedagogical modalities and interaction types emitted by the Teaching Agent."""

    EXPLANATION = "EXPLANATION"
    RETRY = "RETRY"
    HINT = "HINT"
    CONTRAST_EXAMPLE = "CONTRAST_EXAMPLE"
    EXERCISE = "EXERCISE"
    DIALOGUE = "DIALOGUE"
    FREEFORM = "FREEFORM"


class PlanItemKind(StrEnum):
    """Classification of an individual item in a learner's daily plan."""

    REVIEW = "review"
    REMEDIAL = "remedial"
    NEW = "new"


class PlanStatus(StrEnum):
    """Lifecycle status of a daily learning plan."""

    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    INVALID = "invalid"


__all__ = [
    "EventType",
    "PlanItemKind",
    "PlanStatus",
    "TeachingActionKind",
]
