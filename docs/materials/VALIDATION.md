# Materials MVP v0.2 validation — 2026-10-02

## Actual editorial batch added later on 2026-10-02

An actual Codex-assisted editorial batch now contains 12 units, 72 cards and 72 exercises. Three authors cross-reviewed one another's content; 24 independent final reviews and 72 answer-free-paper solutions are retained. All final answers agree, and 46 claims map to 32 cited spans from two MIT textbook documents. This does not represent a live call through the still-unconfigured application model provider or a human approval.

The new batch passes seven real-artifact acceptance tests, strict typing, source/PDF/text/hash verification and independent SQLite/manifest audits. The populated local review dashboard displays lesson titles and explicitly distinguishes unknown editorial costs from application-provider counters; its existing 22 tests, strict typing and Ruff checks pass. Browser inspection confirmed the populated home and a full lesson detail page.

See [the Chinese delivery and quality report](../../materials-workspace/editorial-v1/QUALITY_REPORT_ZH.md) and [the independent data audit](../../materials-workspace/editorial-v1/INDEPENDENT_DATA_AUDIT.md). The source corpus, candidate database and audit workbench remain isolated under `materials-workspace/editorial-v1/`. Prior engineering validation below remains a record of that earlier phase, not a claim that every repository/frontend check was rerun for the content batch.

## Status

The independent local MVP and its available local verification are complete. Live model generation remains pending the user's separate provider configuration. Protected platform captions remain dependent on legitimate platform or creator authorization. Human teaching approval remains a required production gate. These are distinguished from implemented features and deterministic tests below.

## Local verification

| Check | Result |
| --- | --- |
| Complete repository Python suite | **311 passed**, 6 deprecation warnings; final run 4.50 seconds |
| Materials strict type checking | All 10 source modules pass `mypy --strict` |
| Repository Ruff lint | Pass |
| Repository Ruff formatting | Pass; all four pre-existing discrepancies resolved |
| Dependency lock synchronization | Pass; runtime and development dependencies are locked |
| Frontend CI-compatible runtime | Node.js **22.23.3** |
| Frontend locked install, type check and production build | `npm ci`, `npm run lint`, `npm run build` pass; install audit reports zero vulnerabilities |
| Git whitespace check | Pass |
| Local browser | Real review home loaded at `http://127.0.0.1:8765`, visible text and narrow-panel layout inspected |
| Remote GitHub Actions | Not triggered; local checks are not presented as a remote CI result |

Test commands:

```sh
GOALCOACH_ENVIRONMENT=testing GOALCOACH_LLM_API_KEY=ci-mock-token .venv/bin/python -m pytest tests/ -q
.venv/bin/mypy --strict src/goalcoach/materials
.venv/bin/ruff check src/ apps/ tests/
.venv/bin/ruff format --check src/ apps/ tests/
uv lock --check
```

Six warnings concern existing OpenTelemetry and Starlette/AnyIO deprecations. They do not indicate test failures.

## Previously failing API regression resolved

The old API test did not enter the application's lifespan, allowing dependency fallback to working-directory settings/persistence. It also selected an unrelated default answer when the attached exercise was a generated matching exercise.

The repaired test starts the full application lifecycle with an isolated temporary learner database, uses test-only model boundaries, and retains real planning/teaching workers and deterministic grading. It obtains the exact exercise from `ContentService`, including generated matching exercises. Normal and matching cases both assert successful grading and persistence. Ten independent test-process repetitions passed all 20 cases; the working `goalcoach.db` SHA-256 stayed unchanged during those repetitions.

The four production formatting adjustments in `grader_component.py`, `teaching_agent.py`, `worker_factory.py` and `json_sanitizer.py` are AST-equivalent to their originals. They introduce no behavior changes.

## Functional gaps now implemented and tested

- **Dependency-complete release:** multiple approved concepts, transitive prerequisites, deterministic topological ordering, collision detection, cycle/missing-dependency rejection and GoalCoach repository reads.
- **Immutable approvals:** exact content hashes, conservative two-review quality score, current source checks, withdrawal and all owning-run state updates.
- **Durable recovery:** per-task and per-run leases, failed/cancelled attempts, resume reuse, stale-owner rejection and guarded state changes.
- **Safe migrations:** populated historical v1/v2 databases upgrade transactionally to v3; sources, artifacts, approvals and releases survive. Membership backfills, idempotency, incompatible-database rejection and rollback on injected failures are tested.
- **Usage accounting:** returned input/output tokens and optional configured-rate estimates are persisted per attempt. Cached results incur no new attempts; failed and historical unmeasured requests remain explicitly unknown rather than free.
- **Human review page:** readable teaching cards, exercises/answers, sources, scores, immutable packet and dispute history; explicit approval and batch publication forms. Tests check actual handlers, escaping, loopback Host restrictions, same-origin writes, CSRF, malformed forms and absence of GET mutations. Production teacher approval was not fabricated.
- **Source ingestion:** bounded public HTTPS access with checked/pinned DNS, static HTML cleanup, selected native-text PDF pages and authorized SRT/VTT/Bilibili JSON subtitles. Invalid addresses, redirects, oversized/partial responses, malformed subtitles, encrypted/image-only PDFs and incomplete page selections are tested.
- **Provider boundary:** the real PydanticAI structured-output adapter was exercised with mock HTTP. This validates integration code, not a live model or educational content.
- **Repeatable CI:** the workflow now runs materials tests and strict type checking; mypy, python-dotenv and pypdf are declared/locked dependencies.

## Real sources verified

[Source verification report](SOURCES.md) contains exact editions, URLs, access results, license conditions and checksums.

- **87 real evidence spans** in `materials-workspace/source-verification/workbench.db`: 43 from a visually checked page of the MIT official textbook and 44 from a fixed Wikibooks revision.
- **41 native-PDF spans** in the separate `pdf-validation.db`: the same MIT page imported through the new production PDF path. These are a second verification of the same page, not 41 additional unique textbook examples.
- Actual YouTube oEmbed metadata returned Mandarin Corner's identity and a real video title. That video tests connectivity only; it is not beginner-level teaching evidence.
- Bilibili returned a CAPTCHA page. Anonymous YouTube caption access returned 403; the official download endpoint requires authorization. No CAPTCHA or access-control bypass occurred.
- MIT material carries noncommercial/ShareAlike conditions; Wikibooks carries attribution/ShareAlike conditions. Both actual sample registrations are deliberately analysis-only, and neither is a teaching approval or commercial publication grant.

Saved audit artifacts:

- `materials-workspace/source-verification/verification.json`
- `materials-workspace/source-verification/pdf-verification.json`
- The official source PDF, rendered/extracted sample and fetched reference HTML in that same ignored directory.

## Remaining external acceptance steps

| Step | Current evidence and next action |
| --- | --- |
| Live model connection and generation | No `MATERIALS_MODEL`/key configuration is available. User said they will notify when configured. Fill `.materials.env` locally, run `check-model`, then perform a real bounded production run. No alternate provider is silently substituted. |
| Reusable social teaching content | Obtain creator-authorized subtitles/exports or appropriate platform authorization. Metadata access does not supply reproduction rights. The import paths and failure handling already work. |
| Actual curriculum publication | Confirm source uses cover the intended adaptation/distribution context, then review generated content as a human. No real learner-facing curriculum was approved or installed during technical verification. |
| Remote CI | Changes remain local; no authenticated GitHub execution was available. Trigger the updated workflow after the changes are pushed through the normal review process. |

OCR, large-scale crawling, remote multi-user authentication, scheduling and a statistically meaningful learning-effectiveness study remain outside this local MVP. They are not represented as verified capabilities.
