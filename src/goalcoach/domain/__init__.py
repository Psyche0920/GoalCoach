"""GoalCoach domain package exposing core domain models, enums, and retention mathematics."""

from goalcoach.domain.enums import (
    EventType,
    PlanItemKind,
    PlanStatus,
    TeachingActionKind,
)
from goalcoach.domain.events import InboundEvent
from goalcoach.domain.models import (
    ConceptDelta,
    ConceptMastery,
    DailyPlan,
    DomainBaseModel,
    ErrorRecord,
    Exercise,
    GradingResult,
    LearnerState,
    LearningGoal,
    PlanItem,
    PlanUpdate,
    ProgressUpdate,
    RubricScores,
    Score,
    SessionSummary,
    TeachingAction,
    utc_now,
)
from goalcoach.domain.retention import calculate_retention, decayed_retention

__all__ = [
    "ConceptDelta",
    "ConceptMastery",
    "DailyPlan",
    "DomainBaseModel",
    "ErrorRecord",
    "EventType",
    "Exercise",
    "GradingResult",
    "InboundEvent",
    "LearnerState",
    "LearningGoal",
    "PlanItem",
    "PlanItemKind",
    "PlanStatus",
    "PlanUpdate",
    "ProgressUpdate",
    "RubricScores",
    "Score",
    "SessionSummary",
    "TeachingAction",
    "TeachingActionKind",
    "calculate_retention",
    "decayed_retention",
    "utc_now",
]
