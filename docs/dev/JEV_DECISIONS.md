# Jev finite decisions

Set these values in the application's `.env`, then restart the backend:

```env
GOALCOACH_JEV_ENABLED=true
GOALCOACH_JEV_API_KEY=your-openrouter-api-key
GOALCOACH_JEV_BASE_URL=https://openrouter.ai/api/v1
GOALCOACH_JEV_MODEL=typesafe/jev-1.13
```

Create the key at [OpenRouter API Keys](https://openrouter.ai/settings/keys). The key is
read as a masked secret. Jev uses OpenRouter's System One endpoint at
`https://openrouter.ai/api/v1/systemone`; its API accepts the TypeSafe state/questions
contract and returns typed answers with probabilities. Pinning `typesafe/jev-1.13`
keeps the decision model version stable. The ordinary LLM and Jev settings remain
separate, so `GOALCOACH_JEV_API_KEY` must contain an OpenRouter key (it may be the same
key used by `GOALCOACH_LLM_API_KEY`).

Jev selects goal-relevant courses, study priorities, activity kinds and micro-session
durations. For new roadmaps, a second finite-choice request reviews courses excluded
from the first selection and adds any that supply a missing goal capability. It does
not reject the roadmap with a separate whole-set coverage verdict. Code retains
prerequisite ordering, mandatory remediation, same-day exclusions, budget enforcement,
and persistence. Ordinary replanning preserves the existing roadmap.

For routine teaching, Jev selects a canonical exercise, teaching card and strategy in
one request. The app renders verified card explanations, vocabulary and examples.
Free learner questions retain the existing LLM tutor. Grading is unchanged.

Jev choices are used directly without a confidence threshold. Daily course priorities
are ranked by their probability distributions (`2 * P(high) + P(medium)`) and selected
in order until the time budget is filled. The worker still checks nonempty roadmap,
prerequisite ordering, mandatory remediation, same-day exclusions, candidate IDs and
budget limits. Invalid responses, an empty goal selection and provider failures
fall back to the existing workers. Logs explicitly report `Jev planning fallback` or
`Jev teaching fallback`; these paths can still incur LLM latency. Successful decisions
expose a `typesafe:` provider in existing result metadata. `Jev decision request` logs
question count, HTTP status and duration, without input content or credentials.

This is an initial integration, not evidence that course quality or end-to-end speed
matches the original planner. Compare representative free-form goals, repeated errors,
day rollover and live Jev latency before relying on it as the production decision policy.

Official contracts: https://openrouter.ai/docs/guides/community/typesafe-sdk,
https://openrouter.ai/typesafe/jev-1.13, and
https://docs.typesafe.ai/primitives/choice .
