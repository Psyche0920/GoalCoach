# Teaching Agent Evolution: Relevance, MCQ Options & Multi-Level HSK 1–6 Expansion

**Date:** 2026-09-22  
**Contributors:** Team GoalCoach (Senior Engineer, AI Engineer, Prompt Engineer)  
**Scope:** Teaching Agent (`Coach Baobao`), Content Persistence, Planning Agent, Orchestrator, Grader Component, API Routes  

---

## 1. Executive Summary & Context

GoalCoach's interactive tutoring loop has progressed through two major architectural milestones:
1. **Instructional Relevance & Frictionless Interaction:** Ensuring explanations directly bridge to upcoming practice exercises, introducing the empathetic **Coach Baobao** persona, propagating rich multiple-choice options (MCQs), and enabling 1-click answers (`1-4` / `A-D`).
2. **Multi-Level Curriculum Expansion (HSK 1–6):** Decoupling hardcoded HSK 1 restrictions across repositories, services, planners, and API routes to unlock all 126 curriculum concepts in Database #1.

```mermaid
flowchart TD
    subgraph Milestone1 ["Milestone 1: Relevance & Fast-Path MCQs"]
        CS[ContentService] -->|Pre-select Target Practice| TA[Teaching Agent: Coach Baobao]
        TA -->|Grounded Explanation| TAP[TeachingAction + exercise_payload]
        TAP -->|Propagates Options [1-4] / [A-D]| UI[Terminal Harness / Web UI]
        UI -->|Submit '1' or 'A'| GC[GraderComponent: Fast-Path <5ms]
    end

    subgraph Milestone2 ["Milestone 2: HSK 1-6 Expansion"]
        DB[(Database #1: 126 Concepts HSK 1-6)] -->|hsk_level parameter| REPO[ContentRepository.list_concepts]
        REPO --> CS2[ContentService.list_all_concepts]
        CS2 --> PLAN[PlanningWorker: state.goal.target_hsk_level]
        CS2 --> ORCH[DeterministicOrchestrator: Dynamic exercise.hsk_level]
        CS2 --> API[FastAPI: /api/v1/curriculum/concepts?level=2]
    end
```

---

## 2. Milestone 1 Retrospective: Instructional Relevance & MCQ Scaffolding

### A. Context Synchronization & Pre-Selection (Fixing Relevance)
* **Problem:** Previously, the LLM generated an explanation *before* the practice exercise was selected. As a result, explanations were generic and often disconnected from the exercise that followed immediately.
* **Solution:** `TeachingWorker` now pre-selects the upcoming candidate exercise (`_select_candidate_exercise`) and injects the `Target Upcoming Practice` directly into the agent's prompt dependencies.
* **Outcome:** Explanations directly introduce, contextualize, and prepare the learner for the practice task, creating a tight pedagogical bridge.

### B. Empathetic "Coach Baobao" Persona & Scaffolding
* **Problem:** On repeated errors (`failed_attempts >= 2`), the tutor emitted "naked exercises" without coaching, creating frustration.
* **Solution:** Upgraded system prompt to **Coach Baobao**—a warm, observant tutor who:
  - Validates effort ("Mastering Chinese takes patience!").
  - Deconstructs grammatical structures step-by-step prior to retries.
  - Formats core vocabulary into clean Markdown tables (`| Character | Pinyin | Meaning |`).

### C. Rich MCQ Options & 1-Click Answering
* **Problem:** Database #1 already stored options for `meaning_mcq`, `en_to_zh_mcq`, and `dialogue_choice`, but `exercise_payload` was dropping them, forcing beginner students to type raw Hanzi.
* **Solution:**
  - Preserved `options` and `exercise_type` on `TeachingAction.exercise_payload` and the `Exercise` domain model.
  - Supported **1-click answering**: learners can type `1`, `2`, `3`, `4` or `A`, `B`, `C`, `D`.
  - Both `GraderComponent` and `DeterministicOrchestrator` resolve numbers/letters to canonical answer strings deterministically in `<5ms`.

---

## 3. Milestone 2: Unlocking HSK 1–6 Multi-Level Curriculum

### A. Database Audit & Finding
While the runtime database file was historically named `goalcoach_hsk1_learning.db`, an audit of its schema and records showed that it already contains **126 concepts across all six HSK levels**:
* **HSK 1:** 20 concepts (`hsk1_c01` – `hsk1_c20`)
* **HSK 2:** 19 concepts (`hsk2_c01` – `hsk2_c19`)
* **HSK 3:** 20 concepts (`hsk3_c01` – `hsk3_c20`)
* **HSK 4:** 33 concepts (`hsk4_c01` – `hsk4_c33`)
* **HSK 5:** 19 concepts (`hsk5_c01` – `hsk5_c19`)
* **HSK 6:** 15 concepts (`hsk6_c01` – `hsk6_c15`)

However, intermediate code abstractions hardcoded `hsk_level = 1` as a default filter, hiding the rest of the curriculum.

### B. Changes Implemented Across the Stack

| Layer | Component | Changes Made |
| :--- | :--- | :--- |
| **Persistence** | [`ContentRepository.list_concepts()`](file:///mnt/c/Users/Karla/OneDrive/Desktop/GoalCoach/src/goalcoach/infrastructure/persistence/repositories.py) | Parameterized with `hsk_level: int \| None = None`. If `None`, returns all active concepts stably ordered by `(hsk_level, sequence_no)`. If `1..6`, filters to that specific level. |
| **Domain Service** | [`ContentService.list_all_concepts()`](file:///mnt/c/Users/Karla/OneDrive/Desktop/GoalCoach/src/goalcoach/infrastructure/persistence/content_service.py) | Propagated `hsk_level: int \| None = None` through to repository. |
| **Adaptive Planner** | [`PlanningWorker` & `planning_agent.py`](file:///mnt/c/Users/Karla/OneDrive/Desktop/GoalCoach/src/goalcoach/agents/planning_agent.py) | 1. Updated `PLANNING_SYSTEM_PROMPT` for general Mandarin Chinese learners.<br>2. Parameterized `get_curriculum_catalog` tool to query concepts for `state.goal.target_hsk_level`.<br>3. Scoped `_heuristic_fallback` to target level with fallback to full catalog.<br>4. Replaced hardcoded `"Introduction to HSK1"` with dynamic `"Introduction to HSK {target_level}"`. |
| **Orchestrator** | [`DeterministicOrchestrator`](file:///mnt/c/Users/Karla/OneDrive/Desktop/GoalCoach/src/goalcoach/application/orchestrator.py) | In `_handle_answer_submitted()`, dynamically resolved `exercise.hsk_level` from `concept.hsk_level` rather than forcing level 1. |
| **API Endpoints** | [`apps/api/routes/learning_loop.py`](file:///mnt/c/Users/Karla/OneDrive/Desktop/GoalCoach/apps/api/routes/learning_loop.py) | 1. Added query param `level: int \| None = Query(default=None, ge=1, le=6)` to `GET /api/v1/curriculum/concepts`.<br>2. Updated learner aggregate and completion endpoints to compute progress summaries relative to the learner's target level. |

---

## 4. Verification & Testing

The multi-level capabilities are verified by automated integration and unit test suites:
1. **Persistence Integration Tests ([`tests/integration/test_content_repository.py`](file:///mnt/c/Users/Karla/OneDrive/Desktop/GoalCoach/tests/integration/test_content_repository.py)):**
   - `repository.list_concepts(hsk_level=1)` returns exactly 20 concepts.
   - `repository.list_concepts()` unlocks 120+ concepts covering all six HSK levels (`{1, 2, 3, 4, 5, 6}`).
   - `repository.list_concepts(hsk_level=2)` returns HSK 2 concepts with all items having `hsk_level == 2`.
2. **API Endpoint Tests ([`tests/unit/test_api_learning.py`](file:///mnt/c/Users/Karla/OneDrive/Desktop/GoalCoach/tests/unit/test_api_learning.py)):**
   - `GET /api/v1/curriculum/concepts` returns all active concepts.
   - `GET /api/v1/curriculum/concepts?level=2` returns only HSK 2 concepts.

---

## 5. Next Steps: Roadmap for Phases 2 & 3

* **Phase 2: Mix-and-Match Exercise Engine**
  - Add `'matching'` exercise type to domain models and SQLite schema.
  - Implement deterministic `<1ms` grader in `GraderComponent` evaluating student pair submissions (`1C 2A 3D...` or JSON pairs).
  - Implement dynamic synthesis in `ContentService` to construct 5-pair matching exercises from concept vocabulary cards.
* **Phase 3: Bite-Sized Micro-Pedagogy**
  - Introduce Single-Word Spotlight cards (`Word 1 -> Audio -> Check -> Word 2...`).
  - Sequence vocabulary review before full example sentences to reduce cognitive fatigue.
