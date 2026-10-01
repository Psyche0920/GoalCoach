---
name: Feature & Bugfix Workflow
description: Use when building a new feature or fixing a bug in GoalCoach. Covers the house workflow — plan before coding, implement with limit-testing tests, write the changelog entry and sync every version reference to it, pass every CI gate (ruff, uv lock, pytest unit/integration/api, web build), and commit semantically in small logical steps instead of one big commit.
---

# GoalCoach Feature & Bugfix Workflow

Every feature or bugfix in this project follows the same six phases. Do not skip
phases, and do not start Phase 2 while still in plan mode.

Current baseline on this branch: **149 Python tests** (94 unit, 29 integration,
26 API) plus the TypeScript build in `apps/web`.

---

## Phase 0 — Guardrails (always active)

- **Never open, read, print, search, or edit `.env` / `.env.*` files.** All
  configuration is referenced strictly via `src/goalcoach/infrastructure/config.py`.
- Never commit secrets, `.env`, or local databases (`*.db`, `*.db-wal`,
  `*.db-shm`) — verify with `git status` before every commit.
- Work on the **current branch only**. Do not create branches or push unless the
  user asks.

---

## Phase 1 — Plan first (before touching any file)

1. **Read the real code before trusting any plan document.** Specs live under
   `docs/dev/*.md` and drift from reality:
   - Grep for every function/class the plan references. A documented helper may
     not exist; find the *actual* entry point and wire there instead.
   - Map every field/method the plan removes or renames to **all** of its
     readers across `src/`, `tests/`, `apps/`.
   - When frontend behavior changes, audit `apps/web/src/types.ts` and the
     consuming components too — the web app is part of CI.
2. **Verify the math/behavior numerically before writing tests.** Evaluate
   proposed test expectations by hand against the proposed logic. A floor or
   clamp (e.g. `max(0.1, gain)`) can collapse both sides of a comparison to
   identical values and make drafted assertions fail. Fix the parameters (or
   flag the contradiction to the user) *before* implementation.
3. **Present the plan in conversation**: file-by-file changes, exact test
   expectations, which existing tests will need updating and why.
4. **Ask the user about decision points** instead of guessing (removed vs. kept
   fields, test parameter fixes, whether existing tests encoding old behavior
   may be updated). Wait for answers before implementing.
5. If the plan doc is found to be wrong, **update it as the first
   implementation step** so it matches reality.

---

## Phase 2 — Implement + exhaustive tests

Order of work:

1. **Fix the plan/spec doc first** if it diverged from the audit.
2. **Implement** the change across domain → application → agents/infrastructure
   → `apps/web` as needed, following the existing architecture and style:
   Pydantic v2 domain models, deterministic workers with LLM fallbacks,
   orchestrator state transitions, async atomic persistence via
   `await learner_repo.save(state)`.
3. **Write tests that take the feature to its limits** — not just the happy
   path:
   - **Invariants:** exact constants and formulas pinned to computed values,
     not only inequalities.
   - **Boundaries/floors/clamps:** minimum and maximum values, score bounds,
     retry limits, interval minimums.
   - **Monotonicity & ordering:** e.g. longer delay → never smaller gain.
   - **Purity:** engines/services do not mutate their inputs unexpectedly.
   - **Timezone robustness:** naive vs. aware datetimes normalized to UTC.
   - **Legacy data migration:** old persisted shapes still load correctly.
   - **Persistence roundtrip:** save → load through SQLite WAL JSON and assert
     every field survives (use a `tmp_path` database).
   - **Failure paths:** invalid input raises, LLM fallback engages, state never
     corrupts to zero.
   - **API behavior:** add coverage in `tests/api/test_api.py` using the
     canonical fixtures from `tests/fakes.py` (isolated client fixture) for
     anything reachable over HTTP.
4. **Update every existing test that encodes the old behavior** so the full
   suite stays green — a regression gate only matters if it tests the new
   spec. Reuse the test's original *intent* (weighting, gates, counts) and
   re-express it under the new behavior.
5. **Full-stack changes:** update TypeScript types and component contracts in
   `apps/web/src/` alongside the backend change — CI fails the PR on
   `npm run lint` (type check) and `npm run build`.
6. When new exports are needed by tests, add them to the package `__init__.py`.

---

## Phase 3 — Docs & changelog

1. **`CHANGELOG.md`** (Keep a Changelog format, newest entry on top, dated
   today): sections `### Added` / `### Changed` / `### Fixed` / `### Removed`
   as applicable. Be specific: file paths, behavior, what was replaced by what.
   The **top entry's version is the project's release version** (current top:
   `0.1.8`); the next entry gets the next semver bump.
2. **`README.md`**: update any section the change invalidates — the tests badge
   and verification-suite counts (keep them equal to the real suite totals),
   architecture diagram labels, feature bullets, repository layout, and add new
   design docs to "Documentation & References". Refresh stale counts rather
   than leaving them behind.
3. Corrected design docs live under `docs/dev/`.

---

## Phase 4 — Version sync (every reference matches the changelog version)

The changelog entry from Phase 3 is the source of truth. Bump **all** version
references to the same value so they never drift:

| File | Field |
| --- | --- |
| `CHANGELOG.md` | new top entry `## [X.Y.Z] - <date>` |
| `pyproject.toml` | `version = "X.Y.Z"` |
| `src/goalcoach/__init__.py` | `__version__` |
| `apps/api/main.py` | `FastAPI(..., version="X.Y.Z")` |
| `apps/web/package.json` | `version` |
| `apps/web/package-lock.json` | `version` (top-level **and** the root `""` package entry) |

Then refresh and verify the lockfile:

```bash
uv lock           # updates the goalcoach package version inside uv.lock
uv lock --check   # must exit 0
```

Note: the code references historically lagged at `0.1.0` while the changelog
advanced to `0.1.8`. The next version sync must close that gap by setting
every reference to the new changelog version.

Follow **semantic versioning**: minor for new features, patch for fixes,
major for breaking API/schema changes.

---

## Phase 5 — Quality gates (mirror CI; all green before any commit)

CI (`.github/workflows/ci.yml`) runs on `main` PRs and blocks merges. Run the
equivalent locally in order; fix the code before proceeding (apply
`uv run ruff format` for formatting diffs — never hand-edit to work around the
formatter):

```bash
# 0. Lockfile sync
uv lock --check

# 1. Lint (0 errors)
uv run ruff check src/ apps/ tests/

# 2. Format (0 diffs)
uv run ruff format --check src/ apps/ tests/

# 3. Full Python suite — unit + integration + api must all be 100% green
uv run pytest tests/unit/ -q          # 94 tests
uv run pytest tests/integration/ -q   # 29 tests
uv run pytest tests/api/ -q           # 26 tests

# 4. Web type check + build (CI does npm ci first when deps changed)
cd apps/web
npm run lint
npm run build
```

Notes:

- Integration/API tests may need CI-style env locally if they fail on config:
  `GOALCOACH_ENVIRONMENT=testing` and `GOALCOACH_LLM_API_KEY` set to any dummy
  value (CI uses `ci-mock-token`).
- The curriculum DB must exist at `data/database1/goalcoach_hsk1_learning.db`
  (CI rebuilds it from the SQL package; re-create it the same way if missing).
- If a test fails, fix the code — do not delete, skip, or weaken the assertion
  unless the spec itself changed and the docs were updated accordingly.

---

## Phase 6 — Semantic, incremental commits (never one big commit)

Commit in **small logical units**, each independently meaningful and each green.
Stage explicit file lists (`git add <paths>`), never `git add -A`.
Conventional Commits, scoped to the layer:

```text
docs(plan): add audited <feature> implementation plan
feat(domain): <domain model change>
feat(engine): <deterministic logic / worker change>
feat(api): <endpoint / orchestrator change>
feat(web): <apps/web change>
test(engine): cover floors, invariants, roundtrip, API behavior
docs: update README and changelog for <feature>
chore(release): bump version to X.Y.Z
```

Rules:

- **Tests for a feature go with or right after the feature commit** they cover
  — never a single "tests + feature + docs + bump" mega-commit. Cross-cutting
  refactors that only stay green atomically may be one `feat:` commit, but the
  plan docs, release notes, and version bump still go in their own commits.
- The **changelog entry + version bump** lands as its own final
  `chore(release):` commit so every reference moves to the new version in one
  step.
- Run `git status` between commits to ensure nothing is left unstaged and no
  `.env` or `*.db` file slipped in.
- Each commit message body explains *why*, referencing the plan/doc when useful.
- Do not push or open a PR unless the user asks.

---

## Final checklist

- [ ] Plan audited against real code; contradictions resolved with the user
- [ ] Feature implemented following existing architecture and style
- [ ] Tests cover invariants, floors, monotonicity, timezones, migration,
      persistence roundtrip, and API behavior
- [ ] Old-behavior tests updated; all 149 tests green (unit + integration + api)
- [ ] `uv lock --check` 0 · `ruff check` 0 errors · `ruff format --check`
      0 diffs · `npm run lint` + `npm run build` pass
- [ ] CHANGELOG entry added; README counts/badges refreshed
- [ ] Every version reference synced to the new changelog version (Phase 4
      table) + `uv lock` refreshed
- [ ] Committed in semantic, incremental commits on the current branch
- [ ] No `.env` file was ever read or touched
