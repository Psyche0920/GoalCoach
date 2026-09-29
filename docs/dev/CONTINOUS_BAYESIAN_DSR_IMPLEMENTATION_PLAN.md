# Engineering Implementation Plan: Continuous Bayesian DSR Engine

## 1. Mathematical Specifications & Core Invariants

The continuous Bayesian DSR model evaluates retention, memory stability, and intrinsic difficulty on a continuous manifold, replacing discrete step counters.

```
                     Continuous Memory Update Cycle
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Rubric Evaluation:  q = 0.50·s_grammar + 0.35·s_sem + 0.15·s_prag   │
│ 2. Memory Grade:       G = 1.0 + 3.0 · q ∈ [1.0, 4.0]                  │
│ 3. Retrievability:     R(Δt, S) = (1 + 9 · Δt / S)⁻¹                   │
│ 4. Stability Scaling:  S' = S · (1 + c(D) · S⁻⁰·¹⁴ · (e¹⁻ᴿ - 1) · q)   │
│ 5. Mastery Metric:     M = 1.0 - e^(-S / 30.0)                         │
│ 6. Optimal Schedule:   Δt_next = S days (for R_target = 0.90)          │
└────────────────────────────────────────────────────────────────────────┘

```

The system enforces six formal equations:

1. **Continuous Rubric Metric:** GoalCoach's 3-axis rubric ($s_{\text{grammar}}, s_{\text{semantic}}, s_{\text{pragmatic}} \in [0.0, 1.0]$) collapses into unified quality $q$:



$$q = 0.50 \cdot s_{\text{grammar}} + 0.35 \cdot s_{\text{semantic}} + 0.15 \cdot s_{\text{pragmatic}}$$



Quality maps to memory grade $G = 1.0 + 3.0 \cdot q \in [1.0, 4.0]$. A trial passes if $G \ge 2.2$ ($q \ge 0.40$ with core syntactic gates satisfied).


2. **Instantaneous Retrievability Function:** Over elapsed days $\Delta t = \max(0.0, (\text{now} - t_{\text{last}})/86400)$, probability of recall decays via power law calibrated to $R(S, S) = 0.90$:



$$R(\Delta t, S) = \left(1 + \frac{\Delta t}{9 \cdot S}\right)^{-1}$$


3. **Mean-Reverting Difficulty:** Item difficulty $D \in [1.0, 10.0]$ dynamically adapts with mean reversion to baseline $D_0 = 5.0$:

$$D' = D - 0.8 \cdot (G - 3.0)$$


$$D_{\text{new}} = \max\left(1.0, \min\left(10.0, 0.10 \cdot D_0 + 0.90 \cdot D'\right)\right)$$


4. **Stability Evolution with Spacing Gain:**
* **Recall Success ($G \ge 2.2$):** Stability increases proportionally to $(e^{1 - R} - 1)$ so that recall at low retrievability yields larger memory consolidation:

$$S_{\text{new}} = S \cdot \left(1 + \frac{11.0 - D_{\text{new}}}{10.0} \cdot S^{-0.14} \cdot \left(e^{1 - R} - 1\right) \cdot \left(\frac{G}{3.0}\right)^{1.2}\right)$$


* **Recall Lapse ($G < 2.2$):** Stability drops safely without wiping long-term traces to absolute zero:

$$S_{\text{new}} = \max\left(0.2, S \cdot 0.25 \cdot D_{\text{new}}^{-0.3}\right)$$




5. **Latent Mastery Metric:** Automaticity $M \in [0.0, 1.0]$ is achieved when stability reaches $S_{\text{mastery}} = 30.0\text{ days}$:

$$M = 1.0 - e^{-\frac{S_{\text{new}}}{30.0}}$$


6. **Target Spaced Review Interval:** For target retention $R_{\text{target}} = 0.90$, the optimal review delay is:

$$\Delta t_{\text{next}} = 9 \cdot S_{\text{new}} \cdot \left(\frac{1}{R_{\text{target}}} - 1\right) = S_{\text{new}} \text{ days}$$



---

## 2. Domain Schema & Persistence Layer Refactoring

GoalCoach persists learner state in SQLite Database #2 (`goalcoach.db`) with Write-Ahead Logging (WAL). `LearnerStateORM` serializes the `state.mastery` dictionary into a SQLite `JSON` column (`mastery_json`).

```
                     Data Persistence Architecture
┌──────────────────────────────┐       ┌──────────────────────────────┐
│  Pydantic v2 Domain Model    │       │     SQLite WAL Storage       │
│        ConceptMastery        │       │       LearnerStateORM        │
├──────────────────────────────┤       ├──────────────────────────────┤
│ stability: float (S)         │ ───►  │ learner_id: String (PK)      │
│ difficulty: float (D)        │ (json)│ mastery_json: JSON Column    │
│ consecutive_successes: int   │       │ updated_at: String (ISO)     │
└──────────────────────────────┘       └──────────────────────────────┘

```

Because `LearnerStateORM` uses JSON serialization, no raw SQL table migration script (`ALTER TABLE`) is required. Pydantic v2 handles default values and legacy conversion during model validation.

### `src/goalcoach/domain/models.py`

Update `ConceptMastery` to incorporate the DSR state variables and legacy migration fallback:

```python
from __future__ import annotations
from datetime import datetime, timezone
from typing import Annotated, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

Score = Annotated[float, Field(ge=0.0, le=1.0)]

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class DomainBaseModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        validate_assignment=True,
    )

class ConceptMastery(DomainBaseModel):
    concept_id: str = Field(min_length=1)
    
    # --- Continuous DSR Coordinates ---
    stability: float = Field(
        default=1.0, 
        gt=0.0, 
        description="Memory trace half-life in days (S)"
    )
    difficulty: float = Field(
        default=5.0, 
        ge=1.0, 
        le=10.0, 
        description="Intrinsic cognitive difficulty (D)"
    )
    consecutive_successes: int = Field(default=0, ge=0)
    
    # --- Tracked Metrics ---
    mastery_score: Score = Field(default=0.0, description="Long-term mastery M in [0, 1]")
    retention_at_review: Score = Field(default=1.0, description="Retrievability R at last trial")
    evidence_count: int = Field(default=0, ge=0)
    weight: float = Field(default=1.0, gt=0.0)
    last_reviewed_at: datetime = Field(default_factory=utc_now)
    next_review_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_schema(cls, data: Any) -> Any:
        """Ensures backwards compatibility with legacy decay_lambda and interval_days."""
        if isinstance(data, dict):
            if "stability" not in data:
                if "interval_days" in data and float(data["interval_days"]) > 0:
                    data["stability"] = float(data["interval_days"])
                elif "decay_lambda" in data and float(data["decay_lambda"]) > 0:
                    data["stability"] = max(0.5, round(1.0 / float(data["decay_lambda"]), 2))
                else:
                    data["stability"] = 1.0
            if "difficulty" not in data:
                data["difficulty"] = 5.0
            if "consecutive_successes" not in data:
                data["consecutive_successes"] = int(data.get("evidence_count", 0))
        return data

    def calculate_current_retrievability(self, at: datetime | None = None) -> float:
        """Calculates instantaneous retrievability R(t) via power-law forgetting."""
        target_time = at or utc_now()
        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=timezone.utc)
        last_time = self.last_reviewed_at
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
            
        elapsed_days = max(0.0, (target_time - last_time).total_seconds() / 86_400.0)
        return max(0.0, min(1.0, 1.0 / (1.0 + (elapsed_days / (9.0 * self.stability)))))

    def is_review_due(self, at: datetime | None = None) -> bool:
        if self.next_review_at is None:
            return False
        current_time = at or utc_now()
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        review_time = self.next_review_at
        if review_time.tzinfo is None:
            review_time = review_time.replace(tzinfo=timezone.utc)
        return review_time <= current_time

```

---

## 3. Progress Service Pipeline Implementation

Create the standalone deterministic DSR engine and connect it to `apply_grading_to_state` in the application layer.

### `src/goalcoach/application/mastery_engine.py`

```python
from __future__ import annotations
import math
from datetime import datetime, timezone, timedelta
from goalcoach.domain.models import ConceptMastery, GradingResult, RubricScores

class DSREngine:
    """Pure mathematical implementation of the Continuous Bayesian DSR Engine."""

    D_BASELINE: float = 5.0
    S_MASTERY_THRESHOLD: float = 30.0
    TARGET_RETENTION: float = 0.90

    @classmethod
    def calculate_rubric_quality(cls, scores: RubricScores) -> float:
        return float(
            0.50 * scores.grammatical_correctness
            + 0.35 * scores.semantic_precision
            + 0.15 * scores.pragmatic_appropriateness
        )

    @classmethod
    def update_concept_mastery(
        cls,
        current: ConceptMastery,
        grading_result: GradingResult,
        at: datetime | None = None,
    ) -> ConceptMastery:
        now = at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Instantaneous Retrievability
        r_current = current.calculate_current_retrievability(at=now)
        
        # 2. Continuous Grade Conversion
        q = cls.calculate_rubric_quality(grading_result.scores)
        passed = grading_result.passed_gates and (q >= 0.40)
        g = 1.0 + 3.0 * q  # Continuous [1.0, 4.0]

        # 3. Difficulty Adaptation
        d_delta = -0.8 * (g - 3.0)
        d_prime = current.difficulty + d_delta
        d_new = max(1.0, min(10.0, 0.10 * cls.D_BASELINE + 0.90 * d_prime))

        # 4. Stability Scaling
        s_prev = max(0.1, current.stability)
        if passed:
            spacing_bonus = math.exp(1.0 - r_current) - 1.0
            complexity_factor = (11.0 - d_new) / 10.0
            gain = complexity_factor * (s_prev ** -0.14) * spacing_bonus * ((g / 3.0) ** 1.2)
            s_new = s_prev * (1.0 + max(0.1, gain))
            consecutive = current.consecutive_successes + 1
        else:
            s_new = max(0.2, s_prev * 0.25 * (d_new ** -0.3))
            consecutive = 0

        # 5. Latent Mastery
        m_new = max(0.0, min(1.0, 1.0 - math.exp(-s_new / cls.S_MASTERY_THRESHOLD)))

        # 6. Next Spaced Review
        interval_days = max(0.25, s_new)  # At least 6 hours
        next_review = now + timedelta(days=interval_days)

        return current.model_copy(
            update={
                "stability": round(s_new, 4),
                "difficulty": round(d_new, 4),
                "mastery_score": round(m_new, 4),
                "retention_at_review": round(r_current, 4),
                "evidence_count": current.evidence_count + 1,
                "consecutive_successes": consecutive,
                "last_reviewed_at": now,
                "next_review_at": next_review,
            }
        )

```

### `src/goalcoach/application/progress_service.py`

Replace the fixed increment (`+0.25`/`-0.10`) with `DSREngine.update_concept_mastery`:

```python
from datetime import datetime, timezone
from goalcoach.domain.models import Exercise, GradingResult, ConceptMastery, ErrorRecord
from goalcoach.application.mastery_engine import DSREngine
from goalcoach.infrastructure.persistence.repositories import SqliteLearnerRepository

async def apply_grading_to_state(
    learner_id,
    exercise: Exercise,
    result: GradingResult,
    learner_repo: SqliteLearnerRepository,
) -> None:
    state = await learner_repo.get(learner_id)
    if not state:
        return

    concept_id = exercise.concept_id
    current_mastery = state.mastery.get(
        concept_id,
        ConceptMastery(concept_id=concept_id),
    )

    # 1. Deterministic State Mutation via DSR Engine
    updated_mastery = DSREngine.update_concept_mastery(current_mastery, result)
    state.mastery[concept_id] = updated_mastery

    # 2. Update Diagnostic Error Profile
    if not result.passed_gates:
        for code in result.detected_errors:
            err = next((e for e in state.error_profile if e.code == code and e.concept_id == concept_id), None)
            if err:
                err.occurrences += 1
                err.last_seen_at = datetime.now(timezone.utc)
            else:
                state.error_profile.append(ErrorRecord(code=code, concept_id=concept_id, occurrences=1))

    # 3. Dynamic Re-planning Trigger (2+ repeated mistakes)
    if any(e.concept_id == concept_id and e.occurrences >= 2 for e in state.error_profile):
        state.needs_replanning = True

    # 4. Atomic Asynchronous Persistence (SQLite WAL)
    state.updated_at = datetime.now(timezone.utc)
    await learner_repo.save(state)

```

---

## 4. Test Suite Verification & Quality Gates

Create `tests/unit/test_mastery_engine.py` to assert mathematical invariants and repository roundtrip integrity:

```python
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from goalcoach.domain.models import ConceptMastery, RubricScores, GradingResult, LearnerState
from goalcoach.application.mastery_engine import DSREngine
from goalcoach.infrastructure.persistence import (
    LearnerBase,
    SqliteLearnerRepository,
    create_session_factory,
    get_engine,
)

def make_result(passed: bool, grammar: float, semantic: float, pragmatic: float) -> GradingResult:
    return GradingResult(
        exercise_id=uuid4(),
        scores=RubricScores(
            grammatical_correctness=grammar,
            semantic_precision=semantic,
            pragmatic_appropriateness=pragmatic,
        ),
        passed_gates=passed,
        confidence=1.0,
        feedback="Test feedback",
        detected_errors=[] if passed else ["ERR_SYNTAX"],
    )

def test_dsr_spacing_effect_amplification():
    """Recalling at low retrievability must yield a greater stability gain than immediate recall."""
    base = ConceptMastery(concept_id="hsk1_ma", stability=4.0, difficulty=5.0)
    result = make_result(passed=True, grammar=1.0, semantic=1.0, pragmatic=1.0)
    
    immediate = DSREngine.update_concept_mastery(base, result, at=base.last_reviewed_at + timedelta(hours=1))
    delayed = DSREngine.update_concept_mastery(base, result, at=base.last_reviewed_at + timedelta(days=4))
    
    assert delayed.stability > immediate.stability

def test_dsr_rubric_quality_proportionality():
    """Near-perfect answers must consolidate memory more than borderline passes."""
    base = ConceptMastery(concept_id="hsk1_le", stability=4.0)
    perfect = make_result(passed=True, grammar=1.0, semantic=1.0, pragmatic=1.0)
    borderline = make_result(passed=True, grammar=0.6, semantic=0.5, pragmatic=0.4)
    eval_time = base.last_reviewed_at + timedelta(days=3)

    res_perfect = DSREngine.update_concept_mastery(base, perfect, at=eval_time)
    res_borderline = DSREngine.update_concept_mastery(base, borderline, at=eval_time)

    assert res_perfect.stability > res_borderline.stability
    assert res_perfect.mastery_score > res_borderline.mastery_score

def test_dsr_lapse_dampening():
    """A failure must depress stability without wiping out long-term traces entirely."""
    consolidated = ConceptMastery(concept_id="hsk1_de", stability=40.0, difficulty=4.0)
    fail_result = make_result(passed=False, grammar=0.2, semantic=0.1, pragmatic=0.1)

    updated = DSREngine.update_concept_mastery(consolidated, fail_result)

    assert updated.stability < consolidated.stability
    assert updated.stability > 0.5
    assert updated.consecutive_successes == 0

@pytest.mark.asyncio
async def test_dsr_sqlite_json_roundtrip(tmp_path):
    """LearnerStateORM must preserve continuous DSR variables through SQLite JSON persistence."""
    db_file = tmp_path / "test_dsr.db"
    session_factory = create_session_factory(f"sqlite:///{db_file}")
    LearnerBase.metadata.create_all(get_engine(session_factory))
    repo = SqliteLearnerRepository(session_factory)

    learner_id = uuid4()
    state = LearnerState(
        learner_id=learner_id,
        mastery={
            "hsk1_shi": ConceptMastery(
                concept_id="hsk1_shi",
                stability=12.5,
                difficulty=4.2,
                consecutive_successes=3,
                mastery_score=0.342,
            )
        },
    )

    await repo.save(state)
    loaded = await repo.get(learner_id)

    assert loaded is not None
    item = loaded.mastery["hsk1_shi"]
    assert item.stability == pytest.approx(12.5)
    assert item.difficulty == pytest.approx(4.2)
    assert item.consecutive_successes == 3

```

Execute verification to confirm test suite compliance:

```bash
uv run ruff check src/goalcoach tests/unit
uv run ruff format --check src/goalcoach tests/unit
uv run pytest tests/unit/test_mastery_engine.py -v

```