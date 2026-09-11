The **GoalCoach-Mockup** repository implements a Duolingo-style React client and an Express prototype with in-memory caching and client-side heuristics. The **GoalCoach** main repository implements a Python backend with FastAPI, PydanticAI agents, SQLite WAL persistence, and dual-provider LLM failover.

Connecting these codebases requires retiring the Express server (`server.ts`) and routing the React client directly to FastAPI, while aligning the domain state schemas across TypeScript and Python.

---

### 1. Multi-Perspective Analysis

**Principal Product Manager Perspective**

* **Preserving High-Engagement UX:** The Mockup delivers an effective CSL (Chinese as a Second Language) experience: interactive Pinyin mouth/tone articulation labs, Duolingo-style gamified exercise modals, an honest forgetting-curve visualizer, and a slide-over Panda coach drawer.


* **Eliminating the "Mock Illusion":** In `GoalCoach-Mockup`, state progression is partially mocked using browser-session logic and direct client calls to Gemini. The main backend must supply the genuine core learning loop: $\text{Goal} \to \text{Plan} \to \text{Teach} \to \text{Grade} \to \text{State Mutation} \to \text{Adapt}$.


* **Honest Progress Value Proposition:** The frontend displays a composite metric ($\text{Goal Completion} = 45\% \text{ Learned} + 35\% \text{ Mastered} + 20\% \text{ Communication}$). The backend must calculate this deterministically so learner achievements remain stable across sessions.



**Senior Software Architect Perspective**

* **Topology Convergence:** Decommission the Node/Express backend (`server.ts`). Migrate the React/Vite client into the primary frontend consumer, communicating with FastAPI running on port 8000.


* **Contract & Schema Divergence:**
* *Mockup TypeScript:* Uses `ConceptProgress` tracking `learnedPercent`, 40/40/20 `learningEvidence` (cards, practice, output), `successfulSpacedRetrievals`, `evidenceDays`, and `reviewQualityCount`.


* *Main Python Backend:* Uses `ConceptMastery` tracking `mastery_score`, `retention_score`, `interval_days`, and `evidence_count`.


* *Architectural Fix:* Extend the Python backend domain schemas to encapsulate the full `ConceptProgress` and `LearningEvent` lifecycle so no frontend fidelity is lost.




* **Decoupled Execution & Latency Protection:** User submissions (`POST /api/v1/answers`) must evaluate grading via the deterministic fast-path or PydanticAI within 800 ms. State mutations and retention updates must execute in FastAPI `BackgroundTasks` to avoid UI blocking.



**Principal Senior Software Engineer Perspective**

* **Payload Serialization Incompatibility:** The React components consume and emit `camelCase` keys (`learnerId`, `exerciseId`, `dailyAvailableMinutes`, `planItemId`), whereas FastAPI/Pydantic defaults to `snake_case` (`learner_id`, `exercise_id`). Pydantic v2 models must enable `populate_by_name=True` and `alias_generator=to_camel`.


* **Missing Utility Endpoints:** The Mockup relies on `/api/tts` for natural Chinese speech synthesis and `/api/v1/grade-freeform` for scenario writing evaluations. These must be integrated into FastAPI as first-class endpoints.


* **Database Isolation:** Preserve the strict separation between Database #1 (`goalcoach_hsk1_learning.db` - read-only static curriculum) and Database #2 (`goalcoach.db` - mutable learner state with WAL mode).



---

### 2. Gap Analysis: What Does Not Fit & Required Adjustments

| Component | GoalCoach-Mockup (TS)

 | GoalCoach Main (Python)

 | Required Engineering Change |
| --- | --- | --- | --- |
| **Runtime Server** | Express.js (`server.ts`) on port 3000 | Uvicorn / FastAPI on port 8000 | Deprecate `server.ts`. Configure Vite reverse-proxy to FastAPI. |
| **Progress Model** | `ConceptProgress` (40/40/20 evidence rule, `evidenceDays`, `retrievals`) | `ConceptMastery` (simple float scores) | Expand Python `models.py` with `ConceptProgress`, `LearningEvidence`, and `LearningEvent`. |
| **Progress Formula** | $0.45\text{L} + 0.35\text{M} + 0.20\text{C}$ | $\sum(w \cdot M \cdot R) / \sum w$ | Standardize progress calculation in `progress_service.py` to support composite metrics. |
| **Grading Pipeline** | Rule-based regex in `grader.ts` + raw Gemini JSON call | Dual-Route Grader (Deterministic Fast Path + PydanticAI fallback) | Route all answer submissions to `grading_agent.py`. |
| **TTS Speech** | Express `/api/tts` proxying Google TTS with in-memory buffer | None | Implement `GET /api/tts` in FastAPI with an `lru_cache` memory buffer. |
| **Chat Interaction** | `/api/v1/chat` calling raw Gemini with Coach BaoBao prompt | PydanticAI `TeachingAgent` with agentic RAG and tool-calling | Connect `ModernChatDrawer` to `POST /api/v1/tutoring/chat`. |
| **Casing Convention** | `camelCase` across React state and props | `snake_case` across Pydantic domain models | Add `alias_generator = to_camel` to Python `DomainBaseModel`. |

---

### 3. Target System Architecture

```text
               ┌─────────────────────────────────────────────────────────┐
               │           React 18 + Vite Frontend (Port 3000)          │
               │   DailyPlanView  |  PinyinLessonModal  |  DuolingoModal │
               │   ModernChatDrawer  |  RetentionVisualizer  |  TopBar   │
               └────────────────────────────┬────────────────────────────┘
                                            │ Vite Proxy / HTTP REST
                                            ▼
               ┌─────────────────────────────────────────────────────────┐
               │              FastAPI Application (Port 8000)            │
               │                                                         │
               │  /api/v1/learners/*      /api/v1/answers                │
               │  /api/v1/curriculum/*    /api/v1/grade-freeform         │
               │  /api/v1/tutoring/chat   /api/tts                       │
               └────────────┬───────────────────────────┬────────────────┘
                            │                           │
              Synchronous Interaction             Background Tasks (Decoupled)
                            ▼                           ▼
               ┌────────────────────────┐  ┌─────────────────────────────┐
               │      GradingAgent      │  │    Progress & State Engine  │
               │  - Deterministic Match │  │  - Spaced Repetition Math   │
               │  - PydanticAI Fallback │  │  - 40/40/20 Evidence Reducer│
               └────────────┬───────────┘  └──────────────┬──────────────┘
                            │                             │
                            ▼                             ▼
               ┌────────────────────────┐  ┌─────────────────────────────┐
               │   OpenRouter / Ollama  │  │   SQLite DB #2 (goalcoach)  │
               │  Qwen-2.5 / Gemma 4    │  │   WAL Mode, Busy Timeout    │
               └────────────────────────┘  └─────────────────────────────┘

```

---

### 4. Implementation Plan for AGY CLI Agent

#### Phase 1: Harmonize Domain Schemas in Python Backend

Update `src/goalcoach/domain/models.py` to incorporate the progress and blueprint models required by the React components:

```python
# src/goalcoach/domain/models.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field
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

class LearningEvidence(DomainBaseModel):
    card_completion: float = 0.0
    practice_completion: float = 0.0
    output_completion: float = 0.0

class ConceptProgress(DomainBaseModel):
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
    state_version: int
    course_coverage: float
    learned_progress: float
    mastered_progress: float
    goal_completion: float
    goal_scope_learned_percent: float = 0.0
    goal_scope_mastered_percent: float = 0.0
    communication_outcome_percent: float = 0.0
    daily_effective_minutes: float = 0.0

class LearningEvent(DomainBaseModel):
    id: str = Field(default_factory=lambda: f"event_{uuid4().hex[:8]}")
    learner_id: str
    plan_item_id: str
    concept_ids: list[str]
    event_type: Literal["card", "audio", "attempt", "output", "review"]
    started_at: datetime = Field(default_factory=utc_now)
    last_active_at: datetime = Field(default_factory=utc_now)
    active_seconds: int = 60
    estimated_minutes: float = 1.0
    engagement_score: float = 1.0
    grading_result: dict | None = None
    created_at: datetime = Field(default_factory=utc_now)

```

#### Phase 2: Implement Progress Reducer & Completion Service

Create `src/goalcoach/application/progress_reducer.py` to calculate state updates deterministically:

```python
# src/goalcoach/application/progress_reducer.py
from datetime import datetime, timezone, timedelta
from goalcoach.domain.models import ConceptProgress, LearningEvent, LearningEvidence

def reduce_concept_progress(
    current: ConceptProgress,
    event: LearningEvent,
    completes_atomic_unit: bool = False,
    is_spaced_review: bool = False,
) -> ConceptProgress:
    evidence_at = event.started_at or datetime.now(timezone.utc)
    event_day = evidence_at.date()
    last_day = current.last_reviewed_at.date() if current.last_reviewed_at else None
    is_distinct_day = (last_day is None) or (last_day != event_day)

    # 1. 40/40/20 First-Learning Flow
    evidence = current.learning_evidence.model_copy()
    if completes_atomic_unit:
        evidence.card_completion = 1.0
        evidence.practice_completion = 1.0
        evidence.output_completion = 1.0
    elif not is_spaced_review:
        if event.event_type == "card":
            evidence.card_completion = 1.0
        elif event.event_type == "attempt":
            passed = event.grading_result.get("passed_gates", True) if event.grading_result else True
            evidence.practice_completion = max(evidence.practice_completion, 1.0 if passed else 0.5)
        elif event.event_type == "output":
            passed = event.grading_result.get("passed_gates", True) if event.grading_result else True
            evidence.output_completion = max(evidence.output_completion, 1.0 if passed else 0.5)

    learned_percent = min(100.0, 100.0 * (0.4 * evidence.card_completion + 0.4 * evidence.practice_completion + 0.2 * evidence.output_completion))
    evidence_days = current.evidence_days + 1 if is_distinct_day else current.evidence_days

    # 2. Spaced Retrieval Tracking
    quality = event.engagement_score
    if event.grading_result:
        scores = event.grading_result.get("scores", {})
        quality = (scores.get("grammatical_correctness", 1.0) + scores.get("semantic_precision", 1.0) + scores.get("pragmatic_appropriateness", 1.0)) / 3.0

    successful_retrievals = current.successful_spaced_retrievals
    avg_review_quality = current.average_review_quality
    review_count = current.review_quality_count

    if is_spaced_review:
        if (is_distinct_day or (current.next_review_at and current.next_review_at <= evidence_at)) and quality >= 0.75:
            successful_retrievals += 1
        avg_review_quality = ((avg_review_quality * review_count) + quality) / (review_count + 1)
        review_count += 1

    # 3. Mastery Qualification Rule: >=4 retrievals, >=3 distinct days, avg quality >= 0.80
    qualifies_mastery = (successful_retrievals >= 4 and evidence_days >= 3 and avg_review_quality >= 0.80)
    is_mastered = current.is_mastered or qualifies_mastery

    interval = max(1.0, successful_retrievals * 2.0)
    next_review = evidence_at + timedelta(days=interval)

    status = "mastered" if is_mastered else ("almost_mastered" if learned_percent >= 100 else ("learning" if learned_percent > 0 else "not_started"))

    return current.model_copy(update={
        "learned_percent": max(current.learned_percent, learned_percent),
        "learning_evidence": evidence,
        "evidence_days": evidence_days,
        "successful_spaced_retrievals": successful_retrievals,
        "review_quality_count": review_count,
        "average_review_quality": avg_review_quality,
        "is_mastered": is_mastered,
        "status": status,
        "mastery_score": 1.0 if is_mastered else min(1.0, current.mastery_score + 0.25 if is_spaced_review else learned_percent / 100.0 * 0.35),
        "last_reviewed_at": evidence_at,
        "next_review_at": next_review,
    })

```

#### Phase 3: Implement Missing Utility Endpoints (TTS, Freeform, Answers)

In `apps/api/routes/learning.py`, expose the exact REST routes expected by the frontend modals:

```python
# apps/api/routes/learning.py
import re
import httpx
from fastapi import APIRouter, HTTPException, Query, Response, BackgroundTasks, Depends
from goalcoach.domain.models import AnswerSubmission, Exercise, LearningEvent
from goalcoach.agents.grading_agent import grade_submission
from goalcoach.application.progress_reducer import reduce_concept_progress
from goalcoach.infrastructure.persistence.repositories import ContentRepository, SqliteLearnerRepository

router = APIRouter(tags=["learning"])
tts_cache: dict[str, bytes] = {}

@router.get("/api/tts")
async def text_to_speech(text: str = Query(..., min_length=1)):
    clean = re.sub(r"[\p{P}\p{S}\s]+", " ", text).strip()
    if not clean:
        raise HTTPException(status_code=400, detail="No speakable text")
    if clean in tts_cache:
        return Response(content=tts_cache[clean], media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})

    url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=zh-CN&client=tw-ob&q={clean}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code != 200:
            raise HTTPException(status_code=502, detail="TTS upstream error")
        tts_cache[clean] = res.content
        return Response(content=res.content, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})

@router.post("/api/v1/answers")
async def submit_answer(
    submission: AnswerSubmission,
    background_tasks: BackgroundTasks,
    content_repo: ContentRepository = Depends(),
    learner_repo: SqliteLearnerRepository = Depends(),
):
    content_ex = content_repo.get_exercise(str(submission.exercise_id))
    if not content_ex:
        raise HTTPException(status_code=404, detail="Exercise not found")

    exercise = Exercise(
        id=content_ex.exercise_id,
        concept_id=content_ex.concept_id,
        prompt=content_ex.prompt,
        target_instruction=content_ex.instruction or "",
        reference_answers=content_ex.accepted_answers or [],
    )

    result, provider = await grade_submission(exercise, submission)

    # Offload deterministic progress recalculation and SQLite persistence to background
    background_tasks.add_task(
        update_state_on_answer,
        learner_id=str(submission.learner_id),
        concept_id=exercise.concept_id,
        result=result,
        learner_repo=learner_repo,
    )

    return {"gradingResult": result, "provider": provider}

```

#### Phase 4: Configure Frontend Vite Proxy & Standalone Client Transition

### Step 1: Update `apps/web/package.json`

Update the `scripts` section in `apps/web/package.json` so `npm run dev` and `npm run build` invoke Vite directly rather than `server.ts`:

```json
{
  "name": "goalcoach-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "tsc --noEmit"
  },
  "dependencies": {
    "lucide-react": "^0.475.0",
    "motion": "^12.4.7",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "recharts": "^3.10.1",
    "uuid": "^11.1.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.9",
    "@types/node": "^22.13.5",
    "@types/react": "^18.3.18",
    "@types/react-dom": "^18.3.5",
    "@types/uuid": "^10.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "tailwindcss": "^4.0.9",
    "typescript": "^5.7.3",
    "vite": "^6.2.0"
  }
}

```

> **Note on clean dependencies:** Unused backend packages from the mockup (`express`, `@google/genai`, `cors`, `tsx`, `esbuild`, `@types/express`, `@types/cors`) have been pruned. This also resolves the `uuid` version deprecation notice.
> 
> 

---

### Step 2: Configure Vite Reverse Proxy (`apps/web/vite.config.ts`)

Ensure `apps/web/vite.config.ts` points `/api` and `/health` to your running FastAPI backend (`[http://127.0.0.1:8000](http://127.0.0.1:8000)`):

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});

```

---

### Step 3: Remove `server.ts` Artifacts from `tsconfig.json`

Open `apps/web/tsconfig.json` and ensure `"include"` only references browser frontend sources:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": false
  },
  "include": ["src"]
}

```

---

### Step 4: Verification Commands for AGY CLI Agent

Instruct your AGY CLI agent to run the following:

```bash
cd apps/web

# 1. Clean old node_modules & lockfile with outdated server packages
rm -rf node_modules package-lock.json

# 2. Re-install clean frontend-only dependencies
npm install

# 3. Start Vite dev server
npm run dev

```

The frontend will boot on `http://localhost:3000/`. When the client makes calls like `fetch('/api/v1/learners/learner_001')` or `fetch('/api/tts')`, Vite transparently forwards them to FastAPI on port 8000.

---

### 5. AGY CLI Implementation Task List

Use this sequential checklist to execute and track the integration across the repositories:

* [ ] **TASK-INT-01: Domain Schema Expansion**
* Update `src/goalcoach/domain/models.py` with `ConceptProgress`, `LearningEvidence`, `ProgressSummary`, and `LearningEvent`.
* Add `alias_generator = to_camel` and `populate_by_name = True` to `DomainBaseModel`.




* [ ] **TASK-INT-02: Deterministic Progress Reducer**
* Implement `src/goalcoach/application/progress_reducer.py` with the 40/40/20 first-learning rule and mastery qualification criteria.
* Add unit test suite in `tests/unit/test_progress_reducer.py` validating retrieval counting and evidence gating.




* [ ] **TASK-INT-03: Learner State SQLite ORM Extension**
* Update `src/goalcoach/infrastructure/persistence/learner_models.py` to persist `concept_progress` and `learning_events` tables alongside `learner_states`.
* Verify SQLite WAL pragmas (`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`).




* [ ] **TASK-INT-04: Utility & Interaction Endpoints**
* Implement `GET /api/tts` in FastAPI with text normalization and an in-memory buffer.
* Wire `POST /api/v1/answers` to `grading_agent.py` and decouple state updates via `BackgroundTasks`.
* Wire `POST /api/v1/grade-freeform` to evaluate blueprint assessment specs.




* [ ] **TASK-INT-05: Bridge Frontend Agent Chat**
* Connect `ModernChatDrawer.tsx` in the frontend to `POST /api/v1/tutoring/chat` in the FastAPI backend.
* Ensure the agent utilizes curriculum RAG lookup against SQLite Database #1 and ChromaDB.




* [ ] **TASK-INT-06: Frontend Standalone Transition & Vite Proxy**
* **Step 6.1 (Fix Scripts):** In ```apps/web/package.json```, set ```"scripts": { "dev": "vite", "build": "tsc -b && vite build", "preview": "vite preview" }``` and remove backend-only dependencies (```express```, ``@google/genai``, ``cors``, ``tsx``, ``esbuild``).
* **Step 6.2 (Fix TSConfig):** In ``apps/web/tsconfig.json``, change ``"include"`` to ``["src"]`` (strip ``server.ts``).
* **Step 6.3 (Vite Proxy):** Update ``apps/web/vite.config.ts`` to proxy ``/api`` and ``/health`` to ``[http://127.0.0.1:8000](http://127.0.0.1:8000)``.
* **Step 6.4 (Clean Reinstall):** ``Run rm -rf node_modules package-lock.json && npm install && npm run dev`` inside ``apps/web/``




* [ ] **TASK-INT-07: End-to-End Integration Validation**
* Execute a full end-to-end learning loop: launch a Pinyin unit $\to$ submit an answer $\to$ verify grading output $\to$ confirm persistence in `goalcoach.db` $\to$ verify updated retention and mastery curves in the React UI.