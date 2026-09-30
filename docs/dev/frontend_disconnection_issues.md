# Frontend & Backend Disconnection Issues: Learning Loop Audit & Fix Plan

**Date**: 2026-09-30  
**Context**: Investigating frontend stall on the *"Preparing your lesson"* loading screen after incorrect exercise answers and repairing the disconnects between backend event orchestration and frontend UI lifecycle.

---

## 1. Executive Summary

When a learner submits an incorrect answer on the web frontend (`localhost:3000`), the application frequently becomes stuck on a loading screen displaying *"Preparing your lesson"* (or *"Preparing next lesson"*) for 60 to 95+ seconds without advancing. The learner is forced to close the session and manually click a concept on the roadmap to proceed.

A full audit of the learning loop revealed that this behavior is caused by a combination of:
1. **Chained sequential LLM calls (Replanning + Re-teaching)** taking up to 95 seconds without intermediate stage reporting.
2. **Premature UI wipe**: `clearTeachingTurn()` resets the active lesson to `null`, displaying a generic blank placeholder while long backend tasks run.
3. **Teaching Agent tool-call roundtrips**: Redundant agent tool calls to fetch concept cards from SQLite Database #1 double inference latency per teaching turn.
4. **Disconnection between `next_action` and modal buttons**: The modal ignores backend `next_action`, traps the learner into only one button (*"Try a new teaching approach"*), does not preserve lesson selection parameters, and does not provide buttons to continue to the next plan item or retry.
5. **Backend planned item strict linear constraint**: `orchestrator.py` restricted `progress_eligible` to strictly `active_item.id == first_uncompleted.id`, preventing learners from making progress if they skipped a failed lesson to work on another uncompleted planned lesson.

---

## 2. End-to-End Learning Loop & Process Flow Audit

```
       [ Learner Goal ]
              │
              ▼ (GOAL_CREATED)
    ┌───────────────────┐
    │  Planning Agent   │──► Generates DailyPlan (ordered items) & Roadmap
    └───────────────────┘
              │
              ▼ (SESSION_STARTED)
    ┌───────────────────┐
    │  Teaching Agent   │──► Generates TeachingAction & attaches Exercise
    └───────────────────┘
              │
              ▼ (ANSWER_SUBMITTED)
    ┌───────────────────┐
    │ Grader Component  │──► Passes or Fails (rubric / fast-path)
    └───────────────────┘
         │          │
 (Passed)│          │(Failed)
         ▼          ▼
   Item Complete  Mistake recorded
   Progress +0.25 If repeated (≥2) ──► needs_replanning = True (next_action: "plan")
   next_action:   If first failure ──► needs_replanning = False (next_action: "teach")
   "teach" /      
   "complete"
```

### Detailed Event-by-Event Analysis

### 1. `GOAL_CREATED`
- **Backend**: Configures goal, calls Planning Agent to generate initial `DailyPlan` and curriculum roadmap. Returns `next_action="teach"`.
- **Frontend**: Dispatches `GOAL_CREATED`, accepts response, renders Daily Plan and Roadmap views.
- **Status**: Connected and working.

### 2. `SESSION_STARTED`
- **Backend**: Two execution branches:
  - **Branch A (Replanning / Plan Regen)**: If `state.needs_replanning == True` (triggered after repeated mistakes), runs `planning_worker.create_plan(...)` via LLM (~30–68s). Clears `needs_replanning`, persists new plan, returns `replanned=True`, `next_action="teach"`, and `teaching_action=None`.
  - **Branch B (Direct Teaching)**: If no replanning needed, locates the active item (by `requested_plan_item_id` or first uncompleted), runs `teaching_worker.teach_concept(...)` via LLM (~25–45s), attaches curriculum exercise, returns `teaching_action` and `next_action="teach"`.
- **Frontend**:
  - `handleStartAgentSession()` runs Branch A or B.
  - If Branch A returns `!teachingAction && nextAction === 'teach'`, it immediately fires a second `SESSION_STARTED` to execute Branch B.
- **Disconnects**:
  - Both LLM operations run sequentially (60–95s total).
  - `clearTeachingTurn()` wipes the modal to `null` before anything returns, displaying a blank *"Preparing your lesson"* spinner for over a minute.
  - The second call hardcodes `{ entry_source: 'planned' }`, discarding roadmap review context.
  - There is no staged loading indicator to distinguish plan adaptation from lesson generation.

### 3. `HELP_REQUESTED`
- **Backend**: Generates empathetic alternative explanation and alternative exercise.
- **Frontend**: Dispatches `HELP_REQUESTED`, updates active teaching card.
- **Status**: Connected and working.

### 4. `ANSWER_SUBMITTED`
- **Backend**:
  - Validates active teaching turn context.
  - Runs Grader Component (fast-path deterministic match or LLM rubric).
  - On pass: Marks active plan item `completed = True`, applies progress/mastery updates. If all items completed, sets `next_action = "complete"`; otherwise `next_action = "teach"`.
  - On fail: Logs error in error profile, applies mastery decay. If concept error counter reaches $\ge 2$, sets `state.needs_replanning = True` and `next_action = "plan"`. Otherwise `next_action = "teach"`.
- **Frontend**:
  - Receives `gradingResult`, `nextAction`.
  - Displays feedback box.
- **Disconnects**:
  - `TeachingAgentModal` does not receive or consume `next_action`.
  - When `passedGates === false`, the modal only displays a single button: `[ Try a new teaching approach ]`.
  - There is no button to advance to the next uncompleted planned lesson, and no button to immediately retry the exercise.
  - When `passedGates === true` on the final item of the day, `next_action` is `"complete"`, but clicking `"Continue to next lesson"` calls `handleStartAgentSession()` which throws an uncaught error: `"Today’s plan is complete"`.

### 5. `SESSION_ENDED`
- **Backend**: Archives active session and resets session pointers.
- **Frontend**: Closes modal and resets activity timer.
- **Status**: Connected and working.

---

## 3. Root Cause Breakdown

### Cause 1: Chained Sequential LLM Latency (60–95s)
When a mistake repeats on a concept:
1. `ANSWER_SUBMITTED` returns `next_action: "plan"`.
2. The user clicks *"Try a new teaching approach"*, sending `SESSION_STARTED`.
3. Backend runs Planning Agent (~30–68s) and returns `teachingAction: None`.
4. Frontend detects `!data.teachingAction && data.nextAction === 'teach'` and fires a second `SESSION_STARTED`.
5. Backend runs Teaching Agent (~25–45s).
6. Total combined latency: **60–95+ seconds** without any visual feedback of progress.

### Cause 2: UI Context Wiped to Blank Loading State
`handleStartAgentSession()` immediately calls `clearTeachingTurn()`, resetting `teachingAction = null`. In `TeachingAgentModal.tsx`:
```tsx
<h2>{action?.actionKind?.replaceAll('_', ' ') || 'Preparing your lesson'}</h2>
{loading && <p>Adapting the lesson to your goal and progress…</p>}
```
The previous card, explanation, and feedback vanish instantly. To the user, the app appears completely hung.

### Cause 3: Redundant Tool Roundtrips in Teaching Agent
In `teaching_agent.py`, the `teaching_agent` defines `@teaching_agent.tool get_concept_teaching_cards`. Because cards are not included in the initial prompt, the model must emit a tool call, wait for local tool execution, and make a **second roundtrip to OpenRouter**. This doubles inference time per teaching turn (~35–45s instead of ~12–18s).

### Cause 4: Trapped Modal Navigation on Mistakes
In `TeachingAgentModal.tsx`:
```tsx
<button onClick={() => void onContinue()}>
  {gradingResult.passedGates ? 'Continue to next lesson' : 'Try a new teaching approach'}
</button>
```
On mistake, the learner has no option to:
- Move to the next planned item.
- Try again immediately without an LLM re-teach.
Furthermore, `onContinue={() => handleStartAgentSession()}` passes no arguments, causing the backend to default back to the first uncompleted item (the failed item again).

### Cause 5: Strict Sequential Progress Restriction in Backend
In `orchestrator.py` lines 401–405:
```python
progress_eligible = (
    not active_item.completed
    and first_uncompleted is not None
    and str(active_item.id) == str(first_uncompleted.id)
)
```
If a learner skipped a failed item to study another uncompleted item in today's plan, `progress_eligible` became `False`, preventing the completed item from counting toward progress or plan completion.

---

## 4. Implementation Plan

### Phase 1: Backend Connection & Latency Fixes
1. **Pre-inject concept cards into Teaching Agent prompt** (`src/goalcoach/agents/teaching_agent.py`):
   - Format cards from `content_service.get_teaching_cards(concept_id)` into the initial prompt.
   - Retain the tool as fallback but enable single-step inference, cutting teaching latency by ~50%.
2. **Allow flexible advancement in `orchestrator.py`** (`src/goalcoach/application/orchestrator.py`):
   - Update `progress_eligible` for planned lessons so that studying any uncompleted item in the active plan (`not active_item.completed`) counts toward progress and marks that specific item completed.

### Phase 2: Frontend Learning Loop & Modal Flow Connection
1. **Connect `nextAction` and Navigation Choices in `TeachingAgentModal.tsx`**:
   - Pass `nextAction`, `hasMorePlannedLessons`, and `onSkipToNextLesson` to `TeachingAgentModal`.
   - On mistake (`!passedGates`):
     - Display:
       - **"Continue to next lesson"** (if more uncompleted planned lessons exist).
       - **"Try a new teaching approach"** (remediation for this concept).
       - **"Try again"** (clears input and selection to let the learner re-attempt immediately).
   - On complete (`nextAction === 'complete'` or all items done):
     - Display **"Finish today's plan"** (calls `handleCloseAgentSession()`).
   - If `nextAction === 'plan'`, show note: *"Your daily plan is adjusting based on this exercise."*
2. **Smooth, Staged Loading in `App.tsx`**:
   - Keep current card visible during loading; do not call `clearTeachingTurn()` until the new payload is ready.
   - Track `loadingStage: 'idle' | 'planning' | 'teaching'`.
   - Render informative loading copy in the modal header and overlay based on `loadingStage`.
   - When advancing to the next lesson, look up the next uncompleted item from `learnerState.activePlan` and pass its `planItemId` and `conceptId`.
   - Preserve `selection` during the replanning chain so roadmap review remains in review mode.
3. **Daily Plan View Unlocking** (`apps/web/src/components/DailyPlanView.tsx`):
   - Allow learners to click any uncompleted item in today's plan rather than strictly locking all future items.

### Phase 3: Verification & Testing
1. Run automated unit and integration tests (`pytest`).
2. Verify frontend transitions on `localhost:3000`:
   - Pass exercise → continue to next lesson smoothly.
   - Fail exercise → retry exercise, request remedial teaching, or continue to next lesson.
   - Final exercise passed → "Finish today's plan" cleanly closes the session without errors.
3. Update `CHANGELOG.md` and create `docs/dev/changes/learning_loop_connection.md`.
