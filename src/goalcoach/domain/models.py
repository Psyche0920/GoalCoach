"""Core Pydantic v2 domain models, aggregates, and validation invariants for GoalCoach."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from goalcoach.domain.enums import PlanItemKind, PlanStatus, RetrievalMode
from goalcoach.domain.retention import calculate_retention

Score = Annotated[float, Field(ge=0.0, le=1.0)]


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class DomainBaseModel(BaseModel):
    """Base domain model enabling attribute binding and serialization defaults."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
        ser_json_timedelta="float",
    )


# --- 1. Target Goal & Milestones ---


class LearningGoal(DomainBaseModel):
    """Target learning milestone and study availability configuration for a learner."""

    id: UUID = Field(default_factory=uuid4)
    title: str = Field(min_length=1, max_length=255)
    target_hsk_level: int = Field(default=3, ge=1, le=6)
    target_date: datetime | None = None
    daily_available_minutes: int = Field(default=20, gt=0, le=240)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)


# --- 2. Spaced Repetition & Error Tracking ---


class ConceptMastery(DomainBaseModel):
    """Learner's mastery and spaced repetition retention state for a single curriculum concept."""

    concept_id: str = Field(min_length=1, max_length=128)
    mastery_score: Score = 0.0
    retention_score: Score = 1.0
    decay_lambda: float = Field(default=0.05, gt=0.0)
    evidence_count: int = Field(default=0, ge=0)
    interval_days: float = Field(default=1.0, gt=0.0)
    last_reviewed_at: datetime = Field(default_factory=utc_now)
    next_review_at: datetime | None = None
    weight: float = Field(default=1.0, gt=0.0)

    def current_retention(self, at: datetime | None = None) -> float:
        """Calculates current decayed retention probability based on elapsed time."""
        return calculate_retention(
            retention_at_review=self.retention_score,
            last_reviewed_at=self.last_reviewed_at,
            at=at,
            decay_lambda=self.decay_lambda,
        )

    def is_review_due(self, at: datetime | None = None) -> bool:
        """Determines whether a spaced review is currently due for this concept."""
        if self.next_review_at is None:
            return False
        current_time = at or utc_now()
        next_review = self.next_review_at
        if next_review.tzinfo is None and current_time.tzinfo is not None:
            next_review = next_review.replace(tzinfo=timezone.utc)
        elif next_review.tzinfo is not None and current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        return next_review <= current_time


class ErrorRecord(DomainBaseModel):
    """Cataloged recurring grammatical or lexical error with diagnostic examples."""

    code: str = Field(min_length=1, max_length=64)  # e.g., "ERR_LE_GUO_CONFUSION"
    concept_id: str = Field(min_length=1, max_length=128)
    occurrences: int = Field(default=1, ge=1)
    last_seen_at: datetime = Field(default_factory=utc_now)
    examples: list[str] = Field(default_factory=list)


# --- 3. Planning ---


class PlanItem(DomainBaseModel):
    """An individual actionable study item within a daily learning plan."""

    id: UUID = Field(default_factory=uuid4)
    concept_id: str = Field(min_length=1, max_length=128)
    kind: PlanItemKind
    objective: str = Field(min_length=1, max_length=500)
    estimated_minutes: int = Field(gt=0, le=120)
    completed: bool = False


class DailyPlan(DomainBaseModel):
    """A daily curriculum schedule generated for the learner with execution tracking."""

    id: UUID = Field(default_factory=uuid4)
    learner_id: UUID
    date: datetime = Field(default_factory=utc_now)
    status: PlanStatus = PlanStatus.ACTIVE
    items: list[PlanItem] = Field(min_length=1)
    rationale: str = Field(min_length=1, max_length=1000)
    generated_at: datetime = Field(default_factory=utc_now)


# --- 4. Interactive Tutoring & Structured Grading ---


class Exercise(DomainBaseModel):
    """A practice exercise targeting a specific concept with instructional constraints."""

    id: UUID = Field(default_factory=uuid4)
    concept_id: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1)
    target_instruction: str = Field(min_length=1)
    hsk_level: int = Field(default=3, ge=1, le=6)
    reference_answers: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class AnswerSubmission(DomainBaseModel):
    """A learner's response submission to a specific practice exercise."""

    learner_id: UUID
    exercise_id: UUID
    answer: str = Field(min_length=1)
    submitted_at: datetime = Field(default_factory=utc_now)


class RubricScores(DomainBaseModel):
    """Multi-dimensional evaluation scores graded against rubric standards."""

    grammatical_correctness: Score
    semantic_precision: Score
    pragmatic_appropriateness: Score


class GradingResult(DomainBaseModel):
    """Structured evaluation output produced by the grader agent for a learner submission."""

    exercise_id: UUID
    scores: RubricScores
    passed_gates: bool
    confidence: Score
    feedback: str = Field(min_length=1)
    detected_errors: list[str] = Field(default_factory=list)
    evidence: str | None = None
    grader_version: str = Field(default="v1.0.0")


# --- 5. Session & State Aggregate ---


class SessionSummary(DomainBaseModel):
    """Summary record of an interactive tutoring session."""

    session_id: UUID = Field(default_factory=uuid4)
    started_at: datetime
    ended_at: datetime
    concepts_covered: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)


class LearnerState(DomainBaseModel):
    """Top-level aggregate root capturing all learner goals, mastery, errors, and plans."""

    learner_id: UUID = Field(default_factory=uuid4)
    goal: LearningGoal | None = None
    goal_changed: bool = False
    mastery: dict[str, ConceptMastery] = Field(default_factory=dict)
    error_profile: list[ErrorRecord] = Field(default_factory=list)
    active_plan: DailyPlan | None = None
    sessions: list[SessionSummary] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)

    def review_due(self, at: datetime | None = None) -> bool:
        """Checks if any concept in the learner's mastery profile is due for review."""
        return any(concept.is_review_due(at) for concept in self.mastery.values())

    def overall_progress(self, at: datetime | None = None) -> float:
        """Calculates normalized overall progress weighted across active mastery and decayed retention."""
        if not self.mastery:
            return 0.0
        total_weight = sum(item.weight for item in self.mastery.values())
        if total_weight <= 0:
            return 0.0
        weighted_sum = sum(
            item.weight * item.mastery_score * item.current_retention(at)
            for item in self.mastery.values()
        )
        return float(weighted_sum / total_weight)


# --- 6. Event Deltas & Retrieval Requests ---


class ConceptDelta(DomainBaseModel):
    """Delta update describing changes to mastery and retention after a grading event."""

    concept_id: str
    previous_mastery: Score
    new_mastery: Score
    previous_retention: Score
    new_retention: Score
    next_review_at: datetime


class ProgressUpdate(DomainBaseModel):
    """State transition event recording evidence updates and plan invalidations."""

    learner_id: UUID
    exercise_id: UUID
    concept_delta: ConceptDelta
    error_codes_added: list[str] = Field(default_factory=list)
    plan_invalidated: bool = False
    updated_at: datetime = Field(default_factory=utc_now)


class RetrievalRequest(DomainBaseModel):
    """Structured query for retrieving concepts, cards, and exercises from content storage."""

    mode: RetrievalMode
    learner_id: UUID
    concept_id: str | None = None
    hsk_level: int | None = Field(default=None, ge=1, le=6)
    content_type: str | None = None
    semantic_need: str | None = None
    error_codes: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, gt=0, le=20)

    @model_validator(mode="after")
    def validate_keys(self) -> RetrievalRequest:
        """Validates that required keys are present for exact or semantic retrieval modes."""
        if self.mode == RetrievalMode.EXACT and not self.concept_id:
            raise ValueError("Exact retrieval requires a non-empty concept_id")
        if self.mode == RetrievalMode.SEMANTIC and not self.semantic_need:
            raise ValueError("Semantic retrieval requires a non-empty semantic_need")
        return self
