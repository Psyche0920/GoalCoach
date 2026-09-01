"""Domain enumerations for learning plan items, plan execution statuses, and content retrieval modes."""

from enum import StrEnum


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


class RetrievalMode(StrEnum):
    """Strategies for querying curriculum concepts and exercises from the content store."""

    EXACT = "exact"
    STRUCTURED = "structured"
    SEMANTIC = "semantic"
