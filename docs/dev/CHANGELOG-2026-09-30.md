# Changelog — 2026-09-30

Scope: the currently uncommitted planning, teaching recovery, testing, and CI changes.

## 1. Consistent remediation policy

- Added `RemediationPolicy` to align remediation rules across Agent prompts, output validation, and plan post-processing.
- Prioritize roadmap concepts with unresolved remediation counters of at least two. The concept with the highest counter must be the first item and use the remedial kind.
- Allow mandatory remedial concepts to repeat on the same day. Resolved remediation does not qualify for this exception.
- Distinguish historical errors from unresolved remediation counters to avoid scheduling remediation solely because past errors exist.

## 2. Plan and roadmap consistency

- Preserve the stored long-term roadmap during ordinary replanning and validate daily items against it.
- Reject unavailable daily concepts instead of silently removing them and saving a shortened plan.
- Return a retryable error when the Planning Agent is unavailable or produces no valid daily items. The `create_plan` execution path no longer automatically substitutes a deterministic curriculum plan.
- Existing deterministic planning helper methods remain in the codebase; this change removes their automatic invocation from that execution path.

## 3. Teaching session recovery

- Added the `X-GoalCoach-Error` header to HTTP 409 responses to distinguish state conflicts (`STATE_CONFLICT`) from invalid sessions (`SESSION_INVALID`).
- Refresh authoritative state and retry eligible non-answer state conflicts once. Answer submissions are not automatically replayed.
- Clear stale teaching content and grading results, refresh server state, and prompt the learner to resume when a 409 cannot be recovered automatically.
- Show retry-planning, resume-lesson, or return-to-plan actions when the teaching modal has an error and no valid teaching content, based on `nextAction`.
- Synchronize `nextAction` when refreshing learner state so recovery actions reflect backend routing.

## 4. Duplicate request prevention

- Added a shared in-flight guard for starting lessons, requesting help, submitting answers, and ending sessions.
- Prevent another answer submission after a grading result is available.
- Disable the close button while a request is running to reduce conflicting session operations.
- Clear the previous teaching action, grading result, and activity timer when starting a new teaching turn.

## 5. Logging and feedback

- Log rejected Agent outputs at the API boundary.
- Explicitly request English feedback in the Grader prompt.

## 6. Regression tests and CI

- Added planning unit tests covering same-day remediation, persisted roadmap validation, repeat restrictions after remediation is resolved, and model failures without heuristic plan substitution.
- Added API tests covering conflict error codes, rejection of stale answers after failed planning, and successful answer submission after session recovery.
- Updated learner-state fixtures in existing goal-relevance tests.
- Added a model-call stub for workflow tests that previously depended on automatic offline Planning fallback. These tests continue to execute the real `PlanningWorker` post-processing and validation without restoring production fallback behavior.
- Fixed import ordering and Ruff formatting issues.
- Extended CI with API tests, Node.js 22 setup, `npm ci`, frontend type checking, and a production build.

## 7. Validation results and limitations

Local validation results:

| Check | Result |
| --- | --- |
| `uv lock --check` | Passed |
| `uv sync --all-extras --dev` | Completed |
| `ruff check src/ apps/ tests/` | Passed |
| `ruff format --check src/ apps/ tests/` | Passed; 63 Python files conform |
| Full `pytest tests/ -q` suite | 139 passed; 5 OpenTelemetry-related deprecation warnings |
| `npm run lint` | Passed |
| `npm run build` | Passed |
| `git diff --check` | Passed |

Backend checks used Python 3.12.14. The full test suite ran with the testing environment and a mock API token. Live model calls and complete browser interaction flows were not verified.

Local frontend checks used Node.js 26, while CI specifies Node.js 22. Remote GitHub Actions has not run yet; these results establish local validation only, and remote CI remains to be confirmed.
