# Definition of done

A work item is done only when all applicable conditions hold:

- Acceptance criterion is demonstrably satisfied.
- Implementation respects domain and Agent interface contracts.
- Automated unit/integration tests cover expected and failure behavior.
- Formatting and static checks pass.
- No secrets, personal data, or unlicensed content are committed.
- Error behavior and fallback are explicit.
- Relevant documentation and configuration examples are updated.
- Another team member has reviewed the work.

For AI behavior, also require:

- Pydantic validates the structured output.
- Prompt, rubric, and model versions are recorded.
- Latency, tokens, and estimated cost are measurable.
- Relevant human-labelled benchmark cases pass the agreed threshold.
- Known disagreements and limitations are documented.
- Hosted failure behavior and local fallback are tested where applicable.

For a weekly milestone, all exit evidence in `roadmap.md` must be reproducible from a clean environment.
