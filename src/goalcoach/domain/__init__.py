"""GoalCoach domain package exposing core domain models, enums, and retention mathematics."""

from goalcoach.domain.enums import PlanItemKind, PlanStatus, RetrievalMode
from goalcoach.domain.models import (
    AnswerSubmission,
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
    ProgressUpdate,
    RetrievalRequest,
    RubricScores,
    Score,
    SessionSummary,
    utc_now,
)
from goalcoach.domain.retention import calculate_retention, decayed_retention

__all__ = [
    "AnswerSubmission",
    "ConceptDelta",
    "ConceptMastery",
    "DailyPlan",
    "DomainBaseModel",
    "ErrorRecord",
    "Exercise",
    "GradingResult",
    "LearnerState",
    "LearningGoal",
    "PlanItem",
    "PlanItemKind",
    "PlanStatus",
    "ProgressUpdate",
    "RetrievalMode",
    "RetrievalRequest",
    "RubricScores",
    "Score",
    "SessionSummary",
    "calculate_retention",
    "decayed_retention",
    "utc_now",
]
