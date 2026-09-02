# GoalCoach Domain Models Implementation Plan (Pydantic v2)

This specification defines the immutable core domain contracts, mathematical learning models, and validation invariants for the GoalCoach agentic platform. The antigravity CLI agent must implement these models strictly using Pydantic v2, standard library typing, and pure Python without external persistence or framework dependencies.

---

### Target File Structure

```text
src/goalcoach/domain/
├── __init__.py          # Public domain exports
├── models.py            # Primary Pydantic v2 domain models and aggregates
├── retention.py         # Deterministic forgetting curve and spaced repetition math
└── enums.py             # Domain enumerations and string literals
tests/unit/
├── test_models.py       # Pydantic validation, serialization, and edge-case tests
└── test_retention.py    # Numerical tests for exponential decay and progress indices

```

---

### Mathematical Invariants & Formulas

**1. Spaced Repetition Forgetting Curve**
Retention decay follows the exponential forgetting curve:


$$R(t) = R_0 \cdot e^{-\lambda \cdot \Delta t}$$

* $R_0 \in [0.0, 1.0]$: Retention score at the last review event.


* $\lambda > 0$: Concept-specific decay constant (default: $0.05$).


* $\Delta t \ge 0$: Elapsed time in days since `last_reviewed_at`.


* $R(t)$ must clamp strictly between $0.0$ and $1.0$.



**2. Goal Progress Index**
Honest progress is concept-weighted across active mastery and decayed retention:


$$\text{Progress} = \frac{\sum_{i=1}^{N} \left( w_i \cdot M_i \cdot R_i(t) \right)}{\sum_{i=1}^{N} w_i}$$

* $w_i > 0$: Importance weight of concept $i$ (default: $1.0$).


* $M_i \in [0.0, 1.0]$: Mastery score demonstrated in tests.


* $R_i(t) \in [0.0, 1.0]$: Current decayed retention probability.


* If $N = 0$, progress evaluates to $0.0$.



---

### Module Specifications

#### 1. `src/goalcoach/domain/enums.py`

```python
from enum import StrEnum

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

```

---

#### 2. `src/goalcoach/domain/retention.py`

```python
from __future__ import annotations
from datetime import datetime, timezone
import math

def calculate_retention(
    retention_at_review: float,
    last_reviewed_at: datetime,
    at: datetime | None = None,
    decay_lambda: float = 0.05,
) -> float:
    """Computes decayed retention probability R = R_0 * exp(-lambda * delta_t)."""
    if decay_lambda <= 0:
        raise ValueError("decay_lambda must be strictly positive")
    
    target_time = at or datetime.now(timezone.utc)
    if last_reviewed_at.tzinfo is None:
        last_reviewed_at = last_reviewed_at.replace(tzinfo=timezone.utc)
    if target_time.tzinfo is None:
        target_time = target_time.replace(tzinfo=timezone.utc)

    elapsed_seconds = max(0.0, (target_time - last_reviewed_at).total_seconds())
    elapsed_days = elapsed_seconds / 86_400.0

    decayed = retention_at_review * math.exp(-decay_lambda * elapsed_days)
    return max(0.0, min(1.0, decayed))

```

---

#### 3. `src/goalcoach/domain/models.py`

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from goalcoach.domain.enums import PlanItemKind, PlanStatus, RetrievalMode
from goalcoach.domain.retention import calculate_retention

Score = Annotated[float, Field(ge=0.0, le=1.0)]

def utc_now() -> datetime:
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
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(min_length=1, max_length=255)
    target_hsk_level: int = Field(default=3, ge=1, le=6)
    target_date: datetime | None = None
    daily_available_minutes: int = Field(default=20, gt=0, le=240)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)

# --- 2. Spaced Repetition & Error Tracking ---

class ConceptMastery(DomainBaseModel):
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
        return calculate_retention(
            retention_at_review=self.retention_score,
            last_reviewed_at=self.last_reviewed_at,
            at=at,
            decay_lambda=self.decay_lambda,
        )

    def is_review_due(self, at: datetime | None = None) -> bool:
        if self.next_review_at is None:
            return False
        current_time = at or utc_now()
        return self.next_review_at <= current_time

class ErrorRecord(DomainBaseModel):
    code: str = Field(min_length=1, max_length=64)  # e.g., "ERR_LE_GUO_CONFUSION"
    concept_id: str = Field(min_length=1, max_length=128)
    occurrences: int = Field(default=1, ge=1)
    last_seen_at: datetime = Field(default_factory=utc_now)
    examples: list[str] = Field(default_factory=list)

# --- 3. Planning ---

class PlanItem(DomainBaseModel):
    id: UUID = Field(default_factory=uuid4)
    concept_id: str = Field(min_length=1, max_length=128)
    kind: PlanItemKind
    objective: str = Field(min_length=1, max_length=500)
    estimated_minutes: int = Field(gt=0, le=120)
    completed: bool = False

class DailyPlan(DomainBaseModel):
    id: UUID = Field(default_factory=uuid4)
    learner_id: UUID
    date: datetime = Field(default_factory=utc_now)
    status: PlanStatus = PlanStatus.ACTIVE
    items: list[PlanItem] = Field(min_length=1)
    rationale: str = Field(min_length=1, max_length=1000)
    generated_at: datetime = Field(default_factory=utc_now)

# --- 4. Interactive Tutoring & Structured Grading ---

class Exercise(DomainBaseModel):
    id: UUID = Field(default_factory=uuid4)
    concept_id: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1)
    target_instruction: str = Field(min_length=1)
    hsk_level: int = Field(default=3, ge=1, le=6)
    reference_answers: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

class AnswerSubmission(DomainBaseModel):
    learner_id: UUID
    exercise_id: UUID
    answer: str = Field(min_length=1)
    submitted_at: datetime = Field(default_factory=utc_now)

class RubricScores(DomainBaseModel):
    grammatical_correctness: Score
    semantic_precision: Score
    pragmatic_appropriateness: Score

class GradingResult(DomainBaseModel):
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
    session_id: UUID = Field(default_factory=uuid4)
    started_at: datetime
    ended_at: datetime
    concepts_covered: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)

class LearnerState(DomainBaseModel):
    learner_id: UUID = Field(default_factory=uuid4)
    goal: LearningGoal | None = None
    goal_changed: bool = False
    mastery: dict[str, ConceptMastery] = Field(default_factory=dict)
    error_profile: list[ErrorRecord] = Field(default_factory=list)
    active_plan: DailyPlan | None = None
    sessions: list[SessionSummary] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)

    def review_due(self, at: datetime | None = None) -> bool:
        return any(concept.is_review_due(at) for concept in self.mastery.values())

    def overall_progress(self, at: datetime | None = None) -> float:
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
    concept_id: str
    previous_mastery: Score
    new_mastery: Score
    previous_retention: Score
    new_retention: Score
    next_review_at: datetime

class ProgressUpdate(DomainBaseModel):
    learner_id: UUID
    exercise_id: UUID
    concept_delta: ConceptDelta
    error_codes_added: list[str] = Field(default_factory=list)
    plan_invalidated: bool = False
    updated_at: datetime = Field(default_factory=utc_now)

class RetrievalRequest(DomainBaseModel):
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
        if self.mode == RetrievalMode.EXACT and not self.concept_id:
            raise ValueError("Exact retrieval requires a non-empty concept_id")
        if self.mode == RetrievalMode.SEMANTIC and not self.semantic_need:
            raise ValueError("Semantic retrieval requires a non-empty semantic_need")
        return self

```

---

#### 4. `src/goalcoach/domain/__init__.py`

```python
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
)
from goalcoach.domain.retention import calculate_retention

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
]

```

---

### Required Unit Test Assertions

The agent must generate `tests/unit/test_models.py` and `tests/unit/test_retention.py` covering:

* **Boundary Clamping:** `Score` rejects values $< 0.0$ and $> 1.0$ with `ValidationError`.


* **Timezone Resilience:** `calculate_retention` computes accurately whether passed timezone-naive or timezone-aware timestamps.


* **Decay Correctness:**
* $\Delta t = 0 \implies R(t) = R_0$.


* $\Delta t > 0 \implies R(t) < R_0$.




* **Weighted Progress:**
* Empty mastery returns $0.0$.


* $1$ item with Mastery $1.0$, Retention $1.0$, Weight $1.0$ returns $1.0$.


* Multi-concept weighted combinations correctly evaluate $\sum(w \cdot m \cdot r) / \sum w$.




* **JSON Roundtrip Serialization:** Calling `LearnerState.model_validate_json(state.model_dump_json())` preserves all nested structures, UUIDs, datetimes, and float precisions without loss.


* **Conditional Retrieval Validation:** `RetrievalRequest(mode="exact")` raises `ValueError` if `concept_id` is omitted.



---

### Antigravity Agent Action Checklist

```text
1. [ ] Create `src/goalcoach/domain/enums.py` with all StrEnum definitions.
2. [ ] Create `src/goalcoach/domain/retention.py` with `calculate_retention`.
3. [ ] Implement `src/goalcoach/domain/models.py` with all Pydantic v2 schemas and validation logic.
4. [ ] Expose all models via `src/goalcoach/domain/__init__.py`.
5. [ ] Create `tests/unit/test_retention.py` and `tests/unit/test_models.py`.
6. [ ] Execute `ruff check src/goalcoach/domain tests/unit` and `ruff format src/goalcoach/domain tests/unit`.
7. [ ] Run `pytest tests/unit` and verify all tests pass with 100% schema coverage.

```