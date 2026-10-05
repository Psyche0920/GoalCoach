# Teaching Materials Workbench — MVP v0.2

An independent Python application that turns permitted source material into evidence-grounded Chinese teaching units. Code, prompts, commands and documentation are English; Chinese examples and pinyin retain their original languages. The workbench has its own database and provider settings and does not switch GoalCoach's learner database or active curriculum.

## Implemented workflow

1. Register source identity, edition, permission evidence and allowed uses.
2. Import selected native-text PDF pages, UTF-8 text or authorized subtitles, or collect allowlisted public HTML/text.
3. Run eight logical PydanticAI roles: source research, evidence extraction, curriculum design, authoring, knowledge review, teaching review, dispute arbitration and release cataloging.
4. Independently solve exercises with answers hidden, then perform two independent scored reviews.
5. Revise or arbitrate within two bounded cycles. Missing evidence, invalid references, unresolved disagreement or failed quality gates stop production.
6. Let an identified human inspect and approve the exact immutable version.
7. Publish a dependency-complete group of approved units as a SQLite database, Markdown, JSONL, review report and integrity manifest.
8. Revoke a source to withdraw every affected version, release and associated production run.

The combined quality score uses the lower score from each reviewer for each dimension; both reviews must pass and the conservative score must reach 85/100. Publication verifies current source records, approval hashes, ID uniqueness, prerequisite completeness and absence of dependency cycles.

## Setup and independent model settings

Use the repository's existing environment:

```sh
uv sync --all-extras --dev
.venv/bin/python -m goalcoach.materials --help
.venv/bin/python -m goalcoach.materials init
```

Copy `examples/materials/model.env.example` to `.materials.env`, which is ignored by Git, and fill the model ID, endpoint and API key locally. Never add credentials to the example file. The application does not implicitly load GoalCoach's `.env` or reuse its providers. Process `MATERIALS_` variables override an explicitly selected settings file.

```sh
.venv/bin/python -m goalcoach.materials --settings-file .materials.env check-model
```

This command makes one real structured-output request and records its usage. A successful connection check establishes provider compatibility, not teaching quality. Without model credentials the command fails explicitly; there is no fabricated or offline production fallback.

Settings:

| Setting | Default | Purpose |
| --- | --- | --- |
| `MATERIALS_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `MATERIALS_MODEL` | Empty | Explicit model ID required |
| `MATERIALS_API_KEY` | Empty | Explicit provider credential required |
| `MATERIALS_TIMEOUT_SECONDS` | 90 | Maximum 120 seconds per model call |
| `MATERIALS_REQUEST_LIMIT` | 30 | Persistent request-attempt allowance per production run |
| `MATERIALS_INPUT_USD_PER_MILLION` | Unset | Optional input-token rate |
| `MATERIALS_OUTPUT_USD_PER_MILLION` | Unset | Optional output-token rate |

Set both token prices or neither. Successful provider responses supply token counts; prices produce estimates, not provider invoices. Failed calls can still be billed externally, so unmeasured and unpriced attempts remain explicitly unknown. A request allowance is not a dollar spending cap.

## Acquire sources

[Verified sources and their exact limits](SOURCES.md) document actual MIT, Wikibooks, YouTube and Bilibili checks, including saved source samples and hashes. The samples have analysis-only registrations and cannot be passed off as adaptation or redistribution approvals.

```sh
# Original demonstration source; not an official textbook.
.venv/bin/python -m goalcoach.materials import --source examples/materials/source.example.json --file examples/materials/original-example.txt

# Real, explicitly selected native-text PDF pages.
.venv/bin/python -m goalcoach.materials import --source path/to/verified-source.json --file path/to/book.pdf --pdf-page 18

# Creator-authorized SRT, VTT or Bilibili subtitle JSON export.
.venv/bin/python -m goalcoach.materials import --source path/to/verified-source.json --file path/to/authorized-subtitles.vtt --subtitles

# Permitted static text or HTML, with an explicit host allowlist.
.venv/bin/python -m goalcoach.materials collect --source path/to/verified-source.json --allow-host approved.example.org

# Metadata only: grants no transcript or reuse permissions.
.venv/bin/python -m goalcoach.materials source-metadata 'https://www.youtube.com/watch?v=vTVuuJ5xBco'
```

Text and subtitle imports are bounded to 1 MB. PDF imports require explicit 1-based page selection, at most 20 pages from a PDF up to 20 MB; extraction is bounded to 1 MB. Encrypted, invalid and image-only selected pages fail explicitly. OCR is not included. Original PDF/subtitle hashes and precise page/cue/line locators are retained.

The collector uses HTTPS, strict hosts/content types, bounded responses and deadlines, public DNS validation and IP pinning with original TLS hostname verification. It rejects redirects, partial responses, private addresses, CAPTCHA pages and unsupported formats. No cookies, login replay, private subtitle endpoint or CAPTCHA bypass is implemented. Personal-data cleanup is a limited initial filter, not comprehensive anonymization.

## Generate, inspect and resume

Prepare one brief per concept using `examples/materials/brief.example.json`. Specify its stable concept ID, exact level framework, objective, level and prerequisite IDs. Teaching item IDs should be namespaced by concept. Use only sources whose registered permissions cover analysis and adaptation.

```sh
.venv/bin/python -m goalcoach.materials --settings-file .materials.env run --brief path/to/greetings.json --source-id VERIFIED_SOURCE_ID
.venv/bin/python -m goalcoach.materials status
.venv/bin/python -m goalcoach.materials usage --run-id RUN_ID
.venv/bin/python -m goalcoach.materials --settings-file .materials.env run --brief path/to/greetings.json --source-id VERIFIED_SOURCE_ID --resume RUN_ID
```

Repeat `--source-id` for multiple sources. Select no more than 100 evidence spans per unit; use focused chapters instead of silently truncating a textbook. Resume requires the original inputs, model identity and workflow policy. Completed tasks are reused without new requests, while failed attempts remain counted. Active run/task leases prevent concurrent workers from overwriting each other. Crashed workers become recoverable after their 180-second leases expire.

No run is automatically approved. An unresolved run exposes its persisted review and arbitration artifacts for inspection.

## Local human review page

```sh
.venv/bin/python -m goalcoach.materials serve --port 8765
```

Open **http://127.0.0.1:8765**. The page shows runs, usage, readable teaching cards and exercises, evidence, source rights, independent scores, immutable packet data and dispute history. Reviewers enter their name to approve an exact version, then select approved units to publish together. All prerequisites must be selected in the same release.

The service binds only to loopback. Every write requires an exact same-origin request and a per-start CSRF token; HTML is escaped and no external scripts or assets are loaded. This is a local trusted-operator interface, not an authenticated public multi-user service. Provider credentials are never shown.

Equivalent commands:

```sh
.venv/bin/python -m goalcoach.materials inspect VERSION_ID
.venv/bin/python -m goalcoach.materials approve VERSION_ID --hash VERSION_ID --reviewer YOUR_NAME
.venv/bin/python -m goalcoach.materials publish FIRST_VERSION_ID SECOND_VERSION_ID
.venv/bin/python -m goalcoach.materials revoke-source SOURCE_ID --reviewer YOUR_NAME
```

## Storage, release and recovery contracts

Runtime files are stored under ignored `materials-workspace/`; `--db PATH` before a command selects another workbench. Existing v1 and v2 workbenches migrate transactionally to schema v3, preserving source records, tasks, immutable packets, approvals and releases. Unknown or unrelated database schemas are rejected. Claims, reviews and disputes remain typed immutable artifacts, not arbitrary dictionaries passed between components.

A release contains:

- `materials.db`: GoalCoach-compatible content tables, complete prerequisite edges, public provenance and exact release membership.
- `materials.md`: readable bilingual teaching material and sources.
- `materials.jsonl`: one material object per unit, in manifest order.
- `review-report.json`: per-unit knowledge review, teaching review and catalog data.
- `manifest.json`: exact ordered versions, prerequisites and SHA-256 artifact checksums.

Publish builds in a temporary directory and atomically moves the validated result into place before committing its registry record. A crash between rename and commit can leave an unregistered directory; it is never advertised as available, and a retry asks the operator to inspect it. Existing legacy singleton manifests are verified without rewriting them. Consumers must consult the current registry and pin a release during a session. Revocation cannot erase copies already distributed. The workbench never replaces GoalCoach's active database automatically.

## Validation and current external prerequisites

[Validation results](VALIDATION.md) distinguish deterministic tests, live source checks, browser inspection and tests requiring credentials. CI now runs materials tests and strict type checking alongside the existing repository checks.

```sh
.venv/bin/python -m pytest tests/materials -q
.venv/bin/mypy --strict src/goalcoach/materials
.venv/bin/ruff check src/ apps/ tests/
.venv/bin/ruff format --check src/ apps/ tests/
```

Live model generation still requires the separately configured provider. Actual use of protected platform subtitles requires a creator-authorized export or appropriately authorized platform account. Human teaching approval is an intentional publication gate. Large-scale crawling, OCR, a production scheduler, authenticated remote collaboration and a statistically validated learning-effectiveness study are beyond this local MVP.
