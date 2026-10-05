# Teaching Materials Database Multi-Agent System: File and Operating Guide

Scope: the newly added Teaching Materials Workbench and its local editorial/review artifacts. This index does not cover the existing GoalCoach learning agents or the separate Jev integration. File inventory and existing changes were inspected on 2026-10-05.

The system turns registered sources into evidence-backed teaching units through eight logical agent roles, independent blind solving, knowledge and teaching reviews, bounded revision/arbitration, human approval and validated batch publication. It uses an independent workbench and model configuration. It does not automatically replace GoalCoach's learner database or active curriculum.

## Contents

- [Part 1 — Markdown guides and their purposes](#part-1--markdown-guides-locations-and-purposes)
- [Part 2 — Added and modified files](#part-2--added-and-modified-files-changes-and-purposes)
- [Part 3 — Complete operating and run guide](#part-3--complete-operating-and-run-guide)
- [Quick start: inspect the existing 12-unit database](#32-quick-start-inspect-the-existing-teaching-material-database)
- [Configure the model provider](#34-configure-and-check-the-independent-model-provider)
- [Generate a new unit](#36-run-the-multi-agent-production-workflow)
- [Review and approve](#38-review-and-approve-an-exact-version)
- [Publish a batch](#39-publish-an-approved-dependency-complete-batch)

## Part 1 — Markdown Guides: Locations and Purposes

### System operation and verification

| Markdown file | Purpose | Read when |
| --- | --- | --- |
| [Workbench README](docs/materials/README.md) | Main operating guide: setup, independent provider settings, ingestion, generation, resume, local review, approval, publication and recovery contracts. | Starting or operating the system. |
| [Source guide](docs/materials/SOURCES.md) | Exact source editions, evidence locators, acquisition results, usage limits, PDF/subtitle imports and connector boundaries. | Registering or collecting sources. |
| [Validation report](docs/materials/VALIDATION.md) | Recorded engineering and editorial verification, with explicit separation of deterministic tests, live checks and pending external acceptance. | Assessing what was actually verified. |
| [Editorial library README](materials-workspace/editorial-v1/README.md) | Local batch directory map, reproduction commands, read-only database queries and candidate-library boundaries. | Inspecting or rebuilding the first editorial batch. |

### Agent collaboration and editorial instructions

| Markdown file | Purpose | Read when |
| --- | --- | --- |
| [First-batch editorial brief](materials-workspace/editorial-v1/EDITORIAL_BRIEF.md) | Shared author/reviewer contract: audience, output schema, evidence rules, unit map and prerequisites. | Understanding how the first batch was assigned. |
| [Editorial decisions](materials-workspace/editorial-v1/EDITORIAL_DECISIONS.md) | Actual reviewer findings, author responses, adjudication and verification; earlier artifacts remain preserved. | Tracing why content changed. |
| [Revision editorial brief](materials-workspace/editorial-v2/EDITORIAL_BRIEF.md) | Common contract and revision scope for the second editorial batch. It is a task brief, not evidence of a completed release. | Preparing or assessing revisions. |

Application-agent instructions are defined in [agents.py](src/goalcoach/materials/agents.py); deterministic scheduling and gates are implemented in [workflow.py](src/goalcoach/materials/workflow.py). They are not separate per-agent Markdown guides.

### Independent review reports and teaching outputs

| Markdown file | Purpose |
| --- | --- |
| [Knowledge and source review](materials-workspace/astra-validation-v1/reports/SOURCE_REVIEW.md) | Independent checks of source support, Mandarin knowledge, answers and limitations for the reviewed snapshot. |
| [Blind review](materials-workspace/astra-validation-v1/reports/BLIND_REVIEW.md) | Method and findings from independent solving with author answers hidden. |
| [Teaching review](materials-workspace/astra-validation-v1/reports/TEACHING_REVIEW.md) | Teaching scope, cognitive load, exercise clarity, scores and blocking/minor findings. |
| [Supplemental source review](materials-workspace/astra-validation-v1/reports/SUPPLEMENTAL_SOURCE_REVIEW.md) | Assessment of additional character evidence; does not retroactively overwrite earlier verdicts. |
| [Independent data audit](materials-workspace/editorial-v1/INDEPENDENT_DATA_AUDIT.md) | Read-only cross-check of actual SQLite rows, authored units, reviews, blind answers, source extracts and hashes. |
| [Learner book](materials-workspace/editorial-v1/exports/candidate-d4c0198f997fcf7e/LEARNER_BOOK.md) | Learner-facing explanations, Chinese/pinyin examples and exercises, separated from answers. |
| [Teacher guide and answer key](materials-workspace/editorial-v1/exports/candidate-d4c0198f997fcf7e/TEACHER_GUIDE.md) | Teaching scope, answer keys, accepted variants, evidence mapping and reviewer information. |

Guide prose and collaboration instructions are English; Chinese teaching examples and pinyin retain their original language. Existing Chinese documents are preserved: [the original MVP proposal](Proposal/Teaching_Materials_Multi_Agent_MVP_Proposal_ZH.md) provides the design baseline, and [the first-batch quality report](materials-workspace/editorial-v1/QUALITY_REPORT_ZH.md) provides the Chinese delivery summary.

Files under `materials-workspace/` are ignored local artifacts. Their links work in this checkout but require the same workspace artifacts when shared; they will not become available on GitHub merely by committing this index. Candidate exports remain immutable and await the appropriate human approval/publication steps. Historical reports describe their recorded snapshots, not checks rerun for this documentation update.

## Part 2 — Added and Modified Files: Changes and Purposes

“Added” and “modified” below refer to the inspected working tree relative to Git HEAD. Local artifacts are listed separately because Git ignores their directory. The existing implementation changes are documented here; this documentation task does not create those runtime changes.

### Added application modules

| File | Purpose of the addition |
| --- | --- |
| [__init__.py](src/goalcoach/materials/__init__.py) | Defines the independent materials package. |
| [__main__.py](src/goalcoach/materials/__main__.py) | CLI entry point for initialization, provider checking, import/collection, production, inspection, usage, resume, review serving, approval, publication and source revocation. |
| [models.py](src/goalcoach/materials/models.py) | Typed immutable contracts for sources, spans, claims, briefs, material, reviews, decisions, packets, usage and workflow results; explicit error types and role definitions. |
| [agents.py](src/goalcoach/materials/agents.py) | Isolated role prompts, injectable runner protocols, independent `MATERIALS_` settings and the metered PydanticAI provider adapter. |
| [sources.py](src/goalcoach/materials/sources.py) | Bounded public HTTPS acquisition, DNS/address checks, social metadata and subtitle parsing. |
| [ingestion.py](src/goalcoach/materials/ingestion.py) | Source import and text/HTML/PDF extraction into traceable evidence spans. |
| [store.py](src/goalcoach/materials/store.py) | SQLite workbench persistence, migrations, immutable artifacts, task/run leases, attempts, usage, approvals and release records. |
| [workflow.py](src/goalcoach/materials/workflow.py) | Evidence/material validation, role scheduling, blind solving, independent reviews, bounded revision/arbitration and resumable production. |
| [publication.py](src/goalcoach/materials/publication.py) | Approval and source rechecks, dependency-complete batch validation, GoalCoach-compatible exports, integrity manifests and publication/revocation behavior. |
| [dashboard.py](src/goalcoach/materials/dashboard.py) | Local review interface with readable material/evidence/reviews, usage, exact-version approval and batch publication; loopback, same-origin and CSRF checks. |

### Added tests

| File | Verification purpose |
| --- | --- |
| [test_pipeline.py](tests/materials/test_pipeline.py) | Production workflow, saved artifacts, attempts, usage and recovery behavior. |
| [test_gates.py](tests/materials/test_gates.py) | Evidence, review, answer and approval quality gates. |
| [test_batch_publication.py](tests/materials/test_batch_publication.py) | Multi-unit release completeness, dependency ordering, collisions, invalid dependencies and exported content. |
| [test_model_settings.py](tests/materials/test_model_settings.py) | Independent provider configuration and model boundary behavior. |
| [test_sources.py](tests/materials/test_sources.py) | Acquisition restrictions, metadata, subtitle/PDF imports, locators and hashes. |
| [test_migrations.py](tests/materials/test_migrations.py) | Historical workbench upgrades, preservation, incompatibility rejection and rollback. |
| [test_dashboard.py](tests/materials/test_dashboard.py) | Review handlers, readable content, forms, escaping, local access and write protections. |

### Added examples and documentation

| File | Purpose |
| --- | --- |
| [Model settings example](examples/materials/model.env.example) | Template for the independently selected `.materials.env`; contains no real credentials. |
| [Unit brief example](examples/materials/brief.example.json) | Structured production input for one concept. |
| [Source registration example](examples/materials/source.example.json) | Source identity and allowed-use registration template. |
| [Original demonstration text](examples/materials/original-example.txt) | Original sample source for exercising import; not an official textbook. |
| [Pilot source registry](examples/materials/sources/pilot-registry.json) | Machine-readable pilot selection and source decisions. |
| [MIT analysis registration](examples/materials/sources/mit-unit01-analysis.json) | Specific MIT source registration for limited analysis use. |
| [Wikibooks analysis registration](examples/materials/sources/wikibooks-greetings-analysis.json) | Fixed-revision Wikibooks registration for limited analysis use. |
| [Operating guide](docs/materials/README.md), [source guide](docs/materials/SOURCES.md), [validation report](docs/materials/VALIDATION.md) | Operation, provenance/acquisition and verification documentation. |
| [Original proposal](Proposal/Teaching_Materials_Multi_Agent_MVP_Proposal_ZH.md) | Original Chinese design baseline; preserved without translation or modification. |
| [This root index](MATERIALS_SYSTEM_GUIDE.md) | English navigation and file-change map with clickable relative links. |

### Modified repository integration files

| File | Actual change and purpose |
| --- | --- |
| [ci.yml](.github/workflows/ci.yml) | Adds materials strict typing and pipeline tests to CI. Configuration does not establish a completed remote CI run. |
| [.gitignore](.gitignore) | Excludes `materials-workspace/`, `.materials.env` and mypy cache; preserves local artifacts and credentials outside Git. |
| [pyproject.toml](pyproject.toml) | Adds `python-dotenv` and `pypdf`, plus the development `mypy` dependency. |
| [uv.lock](uv.lock) | Locks the updated dependency graph for repeatable installs. |
| [test_api_learning.py](tests/unit/test_api_learning.py) | Isolates learner persistence, enters application lifespan, stubs model I/O and verifies real deterministic grading/persistence for canonical and generated matching exercises. |
| [grader_component.py](src/goalcoach/agents/grader_component.py) | Existing formatting-only adjustment; no added materials behavior. |
| [teaching_agent.py](src/goalcoach/agents/teaching_agent.py) | Existing formatting-only adjustment; no added materials behavior. |
| [worker_factory.py](src/goalcoach/agents/worker_factory.py) | Existing formatting-only adjustment; no added materials behavior. |
| [json_sanitizer.py](src/goalcoach/infrastructure/llm/json_sanitizer.py) | Existing quote-format adjustment with equivalent Python AST; no added materials behavior. |

The untracked [Jev architecture guide](docs/ARCHITECTURE_GUIDE.md) is a separate change and is outside this materials-system inventory.

### Local editorial and database artifacts

| File or directory | Purpose |
| --- | --- |
| [build_library.py](materials-workspace/editorial-v1/build_library.py) | Builds and validates the actual editorial candidate and imports reviewed packets into its isolated workbench. |
| [editorial_schema.py](materials-workspace/editorial-v1/editorial_schema.py) | Typed editorial, blind-paper, review and evidence contracts for the actual batch. |
| [test_candidate_integrity.py](materials-workspace/editorial-v1/test_candidate_integrity.py) | Acceptance checks against real artifacts, including tampering and stale reviews. |
| [units/](materials-workspace/editorial-v1/units/), [blind-papers/](materials-workspace/editorial-v1/blind-papers/), [reviews/](materials-workspace/editorial-v1/reviews/) | Authored units, answer-free inputs and independently produced review/solution artifacts. |
| [history/](materials-workspace/editorial-v1/history/) | Preserved earlier drafts and reviews for revision traceability. |
| [source.json](materials-workspace/editorial-v1/source.json), [supplemental-sources.json](materials-workspace/editorial-v1/supplemental-sources.json), [evidence-index.json](materials-workspace/editorial-v1/evidence-index.json), [sources/](materials-workspace/editorial-v1/sources/) | Registered source uses, supporting documents, exact evidence locators and extracts. |
| [workbench.db](materials-workspace/editorial-v1/workbench.db) | Independent editorial review database; separate from GoalCoach learner state and active curriculum. |
| [Candidate SQLite library](materials-workspace/editorial-v1/exports/candidate-d4c0198f997fcf7e/candidate-library.sqlite3) | Queryable candidate material, evidence, prerequisites and review data; not an installed production curriculum. |
| [packets.jsonl](materials-workspace/editorial-v1/exports/candidate-d4c0198f997fcf7e/packets.jsonl), [manifest.json](materials-workspace/editorial-v1/exports/candidate-d4c0198f997fcf7e/manifest.json) | Structured candidate content and exact artifact identities/checksums. |
| [Source acquisition audit](materials-workspace/source-verification/verification.json), [PDF import audit](materials-workspace/source-verification/pdf-verification.json) | Recorded real-source acquisition and independent native-PDF importer verification. |
| [Independent review result](materials-workspace/astra-validation-v1/VALIDATION_RESULT.json), [review details](materials-workspace/astra-validation-v1/reports/RESULT_DETAILS.json) | Structured independent-review outcomes accompanying the Markdown reports. |

Local candidate libraries and published `materials.db` releases are different artifacts. The application publication path exports approved content to GoalCoach-compatible tables; the current editorial candidate intentionally uses candidate tables and does not establish an approved release.

## Part 3 — Complete Operating and Run Guide

All commands below run from the repository root in a terminal. Keep the terminal open while a review server is running; press `Ctrl+C` to stop it. This section contains the complete local operating sequence, so the linked specialist documents are optional references for deeper detail.

### 3.1 Choose what you want to run

| Goal | Starting point | Model credentials needed? |
| --- | --- | --- |
| Read the existing 12-unit batch and its reviews | Section 3.2 | No |
| Generate a new unit with the application agents | Sections 3.3–3.6 | Yes |
| Resume interrupted generation | Section 3.7 | Yes |
| Approve and publish reviewed units | Sections 3.8–3.9 | No new model calls; reviewed content and source rights must qualify |
| Withdraw content after source revocation | Section 3.10 | No |

Two separate workbenches are used in this guide:

- Existing editorial batch: `materials-workspace/editorial-v1/workbench.db`, review port **8766**.
- New application production: default `materials-workspace/workbench.db`, review port **8765**.

`--db` and `--settings-file` are global options: put them **before** the subcommand. Use the same database path throughout a workflow. Neither review server requires GoalCoach's FastAPI backend, React frontend or learner database.

### 3.2 Quick start: inspect the existing teaching-material database

```sh
cd /Users/hanweijia/GoalCoach

.venv/bin/python -m goalcoach.materials \
  --db materials-workspace/editorial-v1/workbench.db \
  serve --port 8766 \
  --output materials-workspace/editorial-v1/approved-releases
```

Open **http://127.0.0.1:8766/**. Choose a run/unit to inspect teaching cards, exercises and answers, evidence, source uses, independent reviews, blind solutions and version data. No model settings are needed to inspect existing content. The current batch is an editorial candidate; inspection does not approve or publish it. Its source registrations currently cover internal analysis/adaptation, so distribution approval remains blocked until legitimate redistribution rights are established.

For files you can read without a server, open the [learner book](materials-workspace/editorial-v1/exports/candidate-d4c0198f997fcf7e/LEARNER_BOOK.md) or [teacher guide](materials-workspace/editorial-v1/exports/candidate-d4c0198f997fcf7e/TEACHER_GUIDE.md). For a terminal summary:

```sh
.venv/bin/python -m goalcoach.materials \
  --db materials-workspace/editorial-v1/workbench.db status
```

If `.venv/bin/python` is missing or a dependency cannot be imported, complete section 3.3. If this local batch directory is absent in another checkout, obtain the actual local artifacts; an empty newly initialized database cannot recreate these twelve units.

### 3.3 First-time environment and workbench setup

```sh
cd /Users/hanweijia/GoalCoach
uv sync --all-extras --dev
.venv/bin/python -m goalcoach.materials --help
.venv/bin/python -m goalcoach.materials init
```

`init` initializes/migrates the independent default workbench at `materials-workspace/workbench.db`. It does not import sources, generate content or install a curriculum. To use another production workbench, replace the final command with:

```sh
.venv/bin/python -m goalcoach.materials \
  --db materials-workspace/my-batch/workbench.db init
```

Then pass that same `--db` path to every import, generation, status, review and publication command below.

### 3.4 Configure and check the independent model provider

Copy the settings template **once**, if `.materials.env` does not already exist:

```sh
cp -n examples/materials/model.env.example .materials.env
```

Edit `.materials.env` locally and set:

```dotenv
MATERIALS_BASE_URL=https://api.openai.com/v1
MATERIALS_MODEL=YOUR_MODEL_ID
MATERIALS_API_KEY=YOUR_API_KEY
MATERIALS_TIMEOUT_SECONDS=90
MATERIALS_REQUEST_LIMIT=30
```

Use your provider's actual OpenAI-compatible endpoint and model ID. `YOUR_MODEL_ID` and `YOUR_API_KEY` are placeholders. This file is ignored by Git; keep credentials out of example files. The application does not implicitly read GoalCoach's `.env`; process `MATERIALS_` variables override the explicitly selected file. Set both optional input/output token prices or neither. The request limit bounds persisted attempts per production run, not dollar spending.

Verify one real structured-output request:

```sh
.venv/bin/python -m goalcoach.materials \
  --settings-file .materials.env check-model
```

Success prints usage and a connectivity confirmation. It establishes provider compatibility, not teaching quality. This command makes a real model request. Missing credentials or an incompatible response fails explicitly; there is no offline production substitute.

### 3.5 Register and import evidence

The `import`/`collect` commands register the supplied source record and its extracted spans together. For a complete small demonstration, use the original repository sample:

```sh
.venv/bin/python -m goalcoach.materials import \
  --source examples/materials/source.example.json \
  --file examples/materials/original-example.txt
```

The command reports the imported span count and source ID **`original-demo`**. The [source record](examples/materials/source.example.json) explicitly identifies this as an original demonstration, not an official textbook.

For actual material, prepare a truthful source JSON record using the example's schema: stable `source_id`, title/category, publisher, edition, URL, rights evidence, allowed uses, reviewer and source status. Generation requires `analysis` and `adaptation`; human approval/publication also requires `redistribution`. Analysis-only MIT/Wikibooks pilot records do not qualify for production simply because collection succeeded.

The following commands are templates: replace `path/to/...` and the approved host with your actual files and authorized source. Choose the relevant import method:

```sh
# Explicit native-text PDF pages; page numbers are 1-based.
.venv/bin/python -m goalcoach.materials import \
  --source path/to/verified-source.json \
  --file path/to/book.pdf \
  --pdf-page 18 --pdf-page 19

# Authorized SRT, VTT or supported Bilibili subtitle JSON.
.venv/bin/python -m goalcoach.materials import \
  --source path/to/verified-source.json \
  --file path/to/authorized-subtitles.vtt \
  --subtitles

# Permitted static HTML/text; URL is taken from the source record.
.venv/bin/python -m goalcoach.materials collect \
  --source path/to/verified-source.json \
  --allow-host approved.example.org
```

PDF imports allow at most 20 selected pages from a file up to 20 MB; extracted text is bounded to 1 MB. Image-only/encrypted/invalid pages fail; OCR is not implemented. Text and subtitle imports are bounded to 1 MB. The collector accepts bounded public HTTPS HTML/text from explicit hosts and rejects redirects, private addresses and CAPTCHA pages. Social metadata is not transcript evidence or permission to reuse a video.

### 3.6 Run the multi-agent production workflow

For the imported demonstration, run:

```sh
.venv/bin/python -m goalcoach.materials \
  --settings-file .materials.env run \
  --brief examples/materials/brief.example.json \
  --source-id original-demo
```

For your own unit, create a brief matching [brief.example.json](examples/materials/brief.example.json): `concept_id`, observable `objective`, exact `framework`, `hsk_level` and `prerequisite_ids`. Replace the brief path/source ID above. Repeat `--source-id` to select multiple distinct sources. The selected sources must contain no more than 100 evidence spans; import focused chapters rather than an entire textbook.

The workflow performs source research, evidence/claim extraction, curriculum design, authorship, answer-hidden solving, independent knowledge/teaching reviews, bounded revision/arbitration and cataloging. Application code enforces the gates. It does not auto-approve content.

The command returns JSON with `run_id`, `state`, an optional `version_id` and a reason. Save the actual IDs for subsequent commands:

| Result | Next action |
| --- | --- |
| `awaiting_approval` with `version_id` | Inspect the exact version and perform human review. |
| `needs_evidence` | Read the reason, supply adequate evidence and start a run with the corrected inputs. |
| `needs_human` or unresolved arbitration | Inspect persisted findings before deciding how to revise. |
| `interrupted` after a failure | Inspect status/usage and use section 3.7 when the original inputs remain valid. |

Review score thresholds and reviewer agreement do not constitute teacher approval or measured learning effectiveness.

### 3.7 Inspect progress, usage and interrupted runs

Replace uppercase identifiers below with actual IDs, without angle brackets:

```sh
.venv/bin/python -m goalcoach.materials status
.venv/bin/python -m goalcoach.materials usage --run-id RUN_ID
.venv/bin/python -m goalcoach.materials inspect VERSION_ID
```

`status` lists run/version/release IDs and states. `usage` shows persisted attempts, returned tokens and configured-rate cost estimates; unknown or unpriced usage is not treated as free. `inspect` prints the immutable material packet for one version.

Resume the demonstration run with its original inputs:

```sh
.venv/bin/python -m goalcoach.materials \
  --settings-file .materials.env run \
  --brief examples/materials/brief.example.json \
  --source-id original-demo \
  --resume RUN_ID
```

Resume requires the same original brief, sources/evidence, model identity and workflow policy. Completed tasks are reused; failed attempts remain counted. Changed inputs require a new run. An actively leased run cannot be taken over; crashed-worker leases expire after 180 seconds. A restart does not reset request allowances or unresolved quality issues.

### 3.8 Review and approve an exact version

For newly generated content in the default workbench:

```sh
.venv/bin/python -m goalcoach.materials serve --port 8765
```

Open **http://127.0.0.1:8765/**. Review the teaching text, pinyin, exercises, correct/accepted answers, evidence, current source uses, both independent reviews and disputes. Enter your reviewer name and approve the exact version only after review. The page is a local operator interface; it is not a remote multi-user service.

CLI equivalent:

```sh
.venv/bin/python -m goalcoach.materials inspect VERSION_ID
.venv/bin/python -m goalcoach.materials approve VERSION_ID \
  --hash VERSION_ID \
  --reviewer 'Your actual reviewer name'
```

The current CLI uses the packet digest as its `VERSION_ID`, so the same exact value is supplied to `--hash`. Approval requires an `awaiting_approval` version, passing independent reviews and current adaptation/redistribution permissions. Altering content creates a new version that needs review and approval again. Do not invent a reviewer identity or change source permissions merely to make approval succeed.

### 3.9 Publish an approved dependency-complete batch

Select approved units in the review page and publish them together, or use:

```sh
# Single unit with no prerequisites.
.venv/bin/python -m goalcoach.materials publish VERSION_ID

# Multiple units, including every required prerequisite.
.venv/bin/python -m goalcoach.materials publish \
  FIRST_VERSION_ID SECOND_VERSION_ID \
  --output materials-workspace/releases
```

Use the database owning those versions. If publishing from the editorial workbench, pass its `--db` before `publish` and use its chosen output directory. Publication rechecks source uses, approvals, hashes, unique IDs and prerequisite completeness; missing/cyclic dependencies fail rather than producing a partial curriculum.

The command prints the release directory. Each application release contains:

| Output | Purpose |
| --- | --- |
| `materials.db` | GoalCoach-compatible curriculum content, prerequisites and public provenance. |
| `materials.md` | Readable teaching material and sources. |
| `materials.jsonl` | Structured units in release order. |
| `review-report.json` | Knowledge/teaching reviews and catalog data. |
| `manifest.json` | Exact version membership, dependencies and artifact checksums. |

Publication produces an independent snapshot. Installing it into GoalCoach's active curriculum is a separate integration action; no automatic database replacement occurs. The existing editorial `candidate-library.sqlite3` is a candidate artifact, not this published `materials.db`.

### 3.10 Revoke a source and withdraw affected releases

When a source genuinely needs withdrawal, use its owning workbench:

```sh
.venv/bin/python -m goalcoach.materials revoke-source SOURCE_ID \
  --reviewer 'Your actual reviewer name'
.venv/bin/python -m goalcoach.materials status
```

Revocation marks affected versions, runs and releases withdrawn through their recorded lineage. Consumers must consult the current registry before using a release. Revocation cannot erase copies already distributed.

### 3.11 Troubleshooting and engineering checks

| Symptom | Check or resolution |
| --- | --- |
| Review page cannot open | Keep `serve` running and use the exact localhost port. If the port is busy, choose another with `--port` and update the browser URL. |
| Dashboard is empty | Check `--db`. The existing twelve-unit batch requires `editorial-v1/workbench.db`; the default production database is separate. |
| Model configuration or connection fails | Verify `.materials.env`, explicit `--settings-file`, endpoint/model/key and overriding process variables. Retry `check-model` after correcting configuration. |
| Source permission failure | Verify actual source rights and allowed uses. Analysis-only records cannot be used for adaptation/publication. |
| More than 100 evidence spans | Select fewer registered sources or import a focused source chapter under a suitable truthful registration. |
| Resume rejects inputs | Use the original inputs/provider identity/policy, or start a new run for revisions. |
| Approval fails | Check exact version/hash, `awaiting_approval` state, both reviews and current adaptation/redistribution rights. |
| Publication fails | Include all approved prerequisites and resolve duplicate IDs, cycles, stale approvals or withdrawn sources. |
| Output directory exists after a crash | Inspect the directory and registry; an unregistered directory is not an available release. Do not delete or overwrite it blindly. |

For engineering verification, run:

```sh
.venv/bin/python -m pytest tests/materials -q
.venv/bin/mypy --strict src/goalcoach/materials
.venv/bin/ruff check src/ apps/ tests/
.venv/bin/ruff format --check src/ apps/ tests/
```

To validate the existing editorial artifacts separately:

```sh
.venv/bin/python materials-workspace/editorial-v1/build_library.py validate
.venv/bin/python -m pytest materials-workspace/editorial-v1/test_candidate_integrity.py -q
```

These are operator commands, not a claim that a live production run, teacher approval or publication occurred during this documentation update. Earlier measured results and their limits are in [VALIDATION.md](docs/materials/VALIDATION.md).
