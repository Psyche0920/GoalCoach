"""Core Pydantic v2 domain models, aggregates, and validation invariants for GoalCoach."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)
from pydantic.alias_generators import to_camel

from goalcoach.domain.enums import PlanItemKind, PlanStatus, RetrievalMode
from goalcoach.domain.retention import calculate_retention

Score = Annotated[float, Field(ge=0.0, le=1.0)]


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(UTC)


class DomainBaseModel(BaseModel):
    """Base domain model enabling attribute binding and serialization defaults."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
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
            next_review = next_review.replace(tzinfo=UTC)
        elif next_review.tzinfo is not None and current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        return next_review <= current_time


class ErrorRecord(DomainBaseModel):
    """Cataloged recurring grammatical or lexical error with diagnostic examples."""

    code: str = Field(min_length=1, max_length=64)  # e.g., "ERR_LE_GUO_CONFUSION"
    concept_id: str = Field(min_length=1, max_length=128)
    occurrences: int = Field(default=1, ge=1)
    last_seen_at: datetime = Field(default_factory=utc_now)
    examples: list[str] = Field(default_factory=list)


class LearningEvidence(DomainBaseModel):
    """Evidence components for the 40/40/20 first-learning rule."""

    card_completion: float = 0.0
    practice_completion: float = 0.0
    output_completion: float = 0.0


class ConceptProgress(DomainBaseModel):
    """Honest concept progress tracking first-learning evidence and spaced retrievals."""

    learner_id: str
    concept_id: str
    learned_percent: float = 0.0
    learning_evidence: LearningEvidence = Field(default_factory=LearningEvidence)
    learning_completion_version: int = 2
    retention_model_version: int = 2
    mastery_score: Score = 0.0
    retention_at_review: Score = 1.0
    decay_lambda: float = 0.05
    successful_spaced_retrievals: int = 0
    evidence_days: int = 0
    average_quality: Score = 0.0
    quality_evidence_count: int = 0
    review_quality_count: int = 0
    average_review_quality: Score = 0.0
    is_mastered: bool = False
    status: Literal["not_started", "learning", "almost_mastered", "mastered"] = "not_started"
    last_reviewed_at: datetime | None = None
    next_review_at: datetime | None = None


class ProgressSummary(DomainBaseModel):
    """Composite progress metrics across course coverage, learning, and mastery."""

    state_version: int = 1
    course_coverage: float = 0.0
    learned_progress: float = 0.0
    mastered_progress: float = 0.0
    goal_completion: float = 0.0
    goal_scope_learned_percent: float = 0.0
    goal_scope_mastered_percent: float = 0.0
    communication_outcome_percent: float = 0.0
    daily_effective_minutes: float = 0.0


class LearningEvent(DomainBaseModel):
    """Idempotent audit event representing study activities and evaluations."""

    id: str = Field(default_factory=lambda: f"event_{uuid4().hex[:8]}")
    learner_id: str
    plan_item_id: str
    concept_ids: list[str] = Field(default_factory=list)
    event_type: Literal["card", "audio", "attempt", "output", "review"]
    started_at: datetime = Field(default_factory=utc_now)
    last_active_at: datetime = Field(default_factory=utc_now)
    active_seconds: int = 60
    estimated_minutes: float = 1.0
    engagement_score: float = 1.0
    grading_result: dict | None = None
    created_at: datetime = Field(default_factory=utc_now)


# --- 3. Planning ---


class PlanItem(DomainBaseModel):
    """An individual actionable study item within a daily learning plan."""

    id: UUID | str = Field(default_factory=uuid4)
    concept_id: str = Field(min_length=1, max_length=128)
    concept_ids: list[str] = Field(default_factory=list)
    kind: PlanItemKind
    objective: str = Field(min_length=1, max_length=500)
    estimated_minutes: int = Field(gt=0, le=120)
    completed: bool = False


class DailyPlan(DomainBaseModel):
    """A daily curriculum schedule generated for the learner with execution tracking."""

    id: UUID | str = Field(default_factory=uuid4)
    learner_id: UUID | str
    date: datetime = Field(default_factory=utc_now)
    status: PlanStatus = PlanStatus.ACTIVE
    items: list[PlanItem] = Field(min_length=1)
    rationale: str = Field(min_length=1, max_length=1000)
    generated_at: datetime = Field(default_factory=utc_now)


# --- 4. Interactive Tutoring & Structured Grading ---


class Exercise(DomainBaseModel):
    """A practice exercise targeting a specific concept with instructional constraints."""

    id: UUID | str = Field(default_factory=uuid4)
    concept_id: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1)
    target_instruction: str = Field(min_length=1)
    hsk_level: int = Field(default=3, ge=1, le=6)
    reference_answers: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class AnswerSubmission(DomainBaseModel):
    """A learner's response submission to a specific practice exercise."""

    learner_id: UUID | str
    exercise_id: UUID | str
    answer: str = Field(min_length=1)
    submitted_at: datetime = Field(default_factory=utc_now)


class RubricScores(DomainBaseModel):
    """Multi-dimensional evaluation scores graded against rubric standards."""

    grammatical_correctness: Score
    semantic_precision: Score
    pragmatic_appropriateness: Score


class GradingResult(DomainBaseModel):
    """Structured evaluation output produced by the grader agent for a learner submission."""

    exercise_id: UUID | str
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

    learner_id: UUID | str = Field(default_factory=uuid4)
    display_name: str | None = None
    goal: LearningGoal | None = None
    goal_changed: bool = False
    mastery: dict[str, ConceptMastery] = Field(default_factory=dict)
    concept_progress: dict[str, ConceptProgress] = Field(default_factory=dict)
    error_profile: list[ErrorRecord] = Field(default_factory=list)
    active_plan: DailyPlan | None = None
    sessions: list[SessionSummary] = Field(default_factory=list)
    passed_blueprint_ids: list[str] = Field(default_factory=list)
    state_version: int = 1
    today_checked_in: bool = False
    last_check_in_date: str | None = None
    estimated_days_remaining: int | None = None
    today_mistake_exercise_ids: list[str] = Field(default_factory=list)
    today_studied_concept_ids: list[str] = Field(default_factory=list)
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

    learner_id: UUID | str
    exercise_id: UUID | str
    concept_delta: ConceptDelta
    error_codes_added: list[str] = Field(default_factory=list)
    plan_invalidated: bool = False
    updated_at: datetime = Field(default_factory=utc_now)


class RetrievalRequest(DomainBaseModel):
    """Structured query for retrieving concepts, cards, and exercises from content storage."""

    mode: RetrievalMode
    learner_id: UUID | str
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

TeachingActionType = Literal[
    "explain",
    "ask",
    "hint",
    "remediate",
]

TeachingSessionStatus = Literal[
    "active",
    "complete",
    "attempt_limit_reached",
]

class TeachingAction(BaseModel):
    """One pedagogical action selected by the Teaching Agent."""

    action_type: TeachingActionType
    concept_id: str
    content: str
    objective: str
    expected_response: bool = False

    exercise: Exercise | None = None


class TeachingTurn(BaseModel):
    """One completed teaching interaction."""

    action: TeachingAction
    learner_response: str | None = None
    grading_result: GradingResult | None = None


class TeachingSession(BaseModel):
    """Short-term interaction history for the current teaching session."""

    concept_id: str
    turns: list[TeachingTurn] = Field(default_factory=list)
    status: TeachingSessionStatus = "active"