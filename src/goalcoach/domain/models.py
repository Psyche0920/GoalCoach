from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

Score = Annotated[float, Field(ge=0.0, le=1.0)]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlanItemKind(StrEnum):
    REVIEW = "review"
    REMEDIAL = "remedial"
    NEW = "new"


class PlanStatus(StrEnum):
    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    INVALID = "invalid"


class RetrievalMode(StrEnum):
    EXACT = "exact"
    STRUCTURED = "structured"
    SEMANTIC = "semantic"


class RubricScores(BaseModel):
    task_achievement: Score
    grammatical_correctness: Score
    target_concept_mastery: Score
    word_order: Score
    completeness: Score
    vocabulary_appropriateness: Score


class GradingResult(BaseModel):
    exercise_id: UUID
    scores: RubricScores
    passed_gates: bool
    confidence: Score
    feedback: str = Field(min_length=1)
    detected_errors: list[str] = Field(default_factory=list)
    evidence: str | None = None
    grader_version: str


class Exercise(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    concept_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    target_instruction: str = Field(min_length=1)
    hsk_level: int = Field(default=1, ge=1, le=9)
    reference_answers: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class AnswerSubmission(BaseModel):
    learner_id: UUID
    exercise_id: UUID
    answer: str = Field(min_length=1)
    submitted_at: datetime = Field(default_factory=utc_now)


class ConceptMastery(BaseModel):
    concept_id: str = Field(min_length=1)
    mastery: Score = 0.0
    retention: Score = 0.0
    evidence_count: int = Field(default=0, ge=0)
    interval_days: float = Field(default=1.0, gt=0)
    last_reviewed_at: datetime | None = None
    next_review_at: datetime | None = None
    weight: float = Field(default=1.0, gt=0)


class ErrorRecord(BaseModel):
    code: str = Field(min_length=1)
    concept_id: str = Field(min_length=1)
    occurrences: int = Field(default=1, ge=1)
    last_seen_at: datetime = Field(default_factory=utc_now)
    examples: list[str] = Field(default_factory=list)


class PlanItem(BaseModel):
    concept_id: str = Field(min_length=1)
    kind: PlanItemKind
    objective: str = Field(min_length=1)
    estimated_minutes: int = Field(gt=0, le=120)
    completed: bool = False


class DailyPlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    learner_id: UUID
    goal_id: UUID
    date: datetime = Field(default_factory=utc_now)
    items: list[PlanItem] = Field(min_length=1)
    status: PlanStatus = PlanStatus.ACTIVE
    rationale: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=utc_now)


class LearningGoal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(min_length=1)
    target_hsk_level: int = Field(default=1, ge=1, le=9)
    available_minutes_per_day: int = Field(default=20, gt=0, le=240)
    target_date: datetime | None = None
    version: int = Field(default=1, ge=1)


class SessionSummary(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    started_at: datetime
    ended_at: datetime
    concepts: list[str] = Field(default_factory=list)
    summary: str


class LearnerState(BaseModel):
    learner_id: UUID = Field(default_factory=uuid4)
    goal: LearningGoal | None = None
    goal_changed: bool = False
    mastery: dict[str, ConceptMastery] = Field(default_factory=dict)
    errors: list[ErrorRecord] = Field(default_factory=list)
    active_plan: DailyPlan | None = None
    sessions: list[SessionSummary] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)

    def review_due(self, at: datetime | None = None) -> bool:
        now = at or utc_now()
        return any(
            concept.next_review_at is not None and concept.next_review_at <= now
            for concept in self.mastery.values()
        )

    def overall_progress(self) -> float:
        if not self.mastery:
            return 0.0
        total_weight = sum(item.weight for item in self.mastery.values())
        weighted = sum(
            item.weight * item.mastery * item.retention for item in self.mastery.values()
        )
        return weighted / total_weight


class ConceptDelta(BaseModel):
    concept_id: str
    previous_mastery: Score
    new_mastery: Score
    previous_retention: Score
    new_retention: Score
    next_review_at: datetime


class ProgressUpdate(BaseModel):
    learner_id: UUID
    exercise_id: UUID
    concept_delta: ConceptDelta
    error_codes_added: list[str] = Field(default_factory=list)
    plan_invalidated: bool = False
    updated_at: datetime = Field(default_factory=utc_now)


class RetrievalRequest(BaseModel):
    mode: RetrievalMode
    learner_id: UUID
    concept_id: str | None = None
    hsk_level: int | None = Field(default=None, ge=1, le=9)
    content_type: str | None = None
    semantic_need: str | None = None
    error_codes: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, gt=0, le=20)

    @model_validator(mode="after")
    def validate_lookup_key(self) -> RetrievalRequest:
        if self.mode == RetrievalMode.EXACT and not self.concept_id:
            raise ValueError("exact retrieval requires concept_id")
        if self.mode == RetrievalMode.SEMANTIC and not self.semantic_need:
            raise ValueError("semantic retrieval requires semantic_need")
        return self
