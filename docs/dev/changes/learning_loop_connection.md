# Detailed Changes Log: Learning Loop Connection & Navigation Fix

**Date**: 2026-09-30  
**Version**: 0.1.6  
**Topic**: Learning Loop Frontend/Backend Connection & Mistake Progression

---

## 1. Problem Description

When learners made a mistake on an exercise in the frontend (`localhost:3000`):
1. **Prolonged Hang on Loading Screen**: If the error repeated, the orchestrator set `state.needs_replanning = True`. Clicking *"Try a new teaching approach"* triggered a first `SESSION_STARTED` to run the Planning Agent (30–68s), followed by a second `SESSION_STARTED` to run the Teaching Agent (25–45s). Total sequential wait time was 60–95+ seconds.
2. **UI Blanking & State Wipe**: `handleStartAgentSession()` in `App.tsx` immediately called `clearTeachingTurn()`, resetting `teachingAction = null`. This caused `TeachingAgentModal.tsx` to wipe all previous content, explanations, and feedback, rendering a blank screen with generic fallback text: *"Preparing your lesson... Adapting the lesson to your goal and progress…"*.
3. **No Direct Progression or Retry Option**: On mistake (`passedGates === false`), the modal only provided a single button: *"Try a new teaching approach"*. Learners could not skip to the next planned item, could not retry the exercise directly, and were trapped on the same lesson unless they closed the modal and clicked a concept from the roadmap.
4. **Context Loss on Continue**: In `App.tsx`, `onContinue` called `handleStartAgentSession()` without arguments, defaulting to `{ entrySource: 'planned' }` with no `planItemId`, causing the backend to default back to the first uncompleted item (the failed item again) and stripping roadmap selection context.
5. **Double Roundtrips in Teaching Agent**: The `teaching_agent` required an intermediate tool call (`get_concept_teaching_cards`) to fetch vocabulary cards from SQLite Database #1, doubling latency for every teaching turn.
6. **Rigid Linear Ordering in Backend**: In `orchestrator.py`, `progress_eligible` strictly required `str(active_item.id) == str(first_uncompleted.id)`. Skipping a failed lesson to study another uncompleted item in today's plan was incorrectly marked as not progress-eligible.
7. **Unhandled Plan Completion Error**: When completing the last lesson of the day, clicking continue threw an unhandled error: `"Today's plan is complete."`.

---

## 2. Fixes & Solutions

1. **Teaching Agent Latency Optimization**: Pre-injected curriculum cards, communicative goal, grammar focus, and vocabulary focus into the prompt in `src/goalcoach/agents/teaching_agent.py`, allowing the model to produce `TeachingAction` in 1 single inference step instead of 2 roundtrips.
2. **Flexible Planned Progress Eligibility**: In `src/goalcoach/application/orchestrator.py`, updated `progress_eligible = not active_item.completed` for planned study, allowing any uncompleted planned item in today's active plan to count toward progress and mark that item completed.
3. **Rich Navigation Controls on Mistakes**: In `TeachingAgentModal.tsx`, added direct actions on mistake:
   - *"Try again"*: Clears the answer and allows immediate re-attempt.
   - *"Try a new teaching approach"*: Requests remedial re-teaching.
   - *"Skip to next lesson"*: Advances to the next uncompleted planned item.
   - *"Finish today's plan"*: Cleanly closes the modal when all items are done.
4. **Phased Loading Feedback & Card Context Preservation**:
   - Added `loadingStage` (`'idle' | 'planning' | 'teaching'`) with dedicated banners (*"Adapting your study plan based on your recent progress..."* vs *"Coach Baobao is crafting your next lesson..."*).
   - Removed premature `clearTeachingTurn()` on session start so the existing card stays visible in the background at reduced opacity while the next lesson loads.
5. **Selection Preservation in Re-planning Chain**: In `App.tsx`, preserved `selection.entrySource`, `selection.conceptId`, and `selection.planItemId` across chained turns and defaulted to `lastLessonSelection.current`.
6. **Daily Plan Unlocking**: In `DailyPlanView.tsx`, set `canOpen = true` for all planned items so learners can click any uncompleted item to study.

---

## 3. Target Files & Changed Lines

| File | Changes Made |
| :--- | :--- |
| `src/goalcoach/agents/teaching_agent.py` | Lines 188–215: Pre-fetched and injected curriculum cards and concept metadata into prompt. |
| `src/goalcoach/application/orchestrator.py` | Lines 401–402: Updated `progress_eligible = not active_item.completed`. |
| `apps/web/src/types.ts` | Lines 428–431: Added `needsReplanning?: boolean` to `LearnerState`. |
| `apps/web/src/components/TeachingAgentModal.tsx` | Lines 7–16: Added `loadingStage`, `nextAction`, `hasMorePlannedLessons`, `onSkipToNextLesson`, `onRetryExercise` props.<br>Lines 117–145: Added phased `loadingMessage`, banner, and preserved card visibility.<br>Lines 312–355: Added *"Try again"*, *"Skip to next lesson"*, and *"Finish today's plan"* button actions. |
| `apps/web/src/App.tsx` | Lines 1, 34: Imported `useMemo`, added `loadingStage` state.<br>Lines 250–290: Added `uncompletedPlanItems`, `nextUncompletedItem`, `handleSkipToNextLesson`, `handleRetryExercise`.<br>Lines 290–330: Updated `handleStartAgentSession` with stage tracking, selection retention, and graceful completion.<br>Lines 400–415: Ensured `clearTeachingTurn` on `handleCloseAgentSession`.<br>Lines 500–525: Passed new navigation and stage props to `TeachingAgentModal`. |
| `apps/web/src/components/DailyPlanView.tsx` | Line 82: Set `canOpen = true` to allow clicking any uncompleted planned item. |
| `CHANGELOG.md` | Added version `[0.1.6] - 2026-09-30`. |
| `docs/dev/frontend_disconnection_issues.md` | Full learning loop audit and implementation plan. |

---

## 4. Verification Results

- `npm run build --prefix apps/web`: Built successfully in 641ms (0 TypeScript / Vite errors).
- `.venv/bin/ruff check src/ tests/`: All checks passed (0 lint errors).
- `.venv/bin/pytest`: All 147 unit and integration tests passed in 1.24s.
