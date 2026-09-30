# Hybrid Autonomous Testing Agent & Telemetry Architecture

This specification defines the architecture, workflow, and implementation roadmap for the **GoalCoach Hybrid Testing Suite**. 

The suite combines high-throughput deterministic testing (for automated CI/CD gating) with an autonomous AI browser testing agent (for exploratory cognitive/visual validation), both feeding into an embedded DuckDB telemetry pipeline.

---

## 1. The Hybrid Architectural Strategy

Enterprise testing requires balancing two competing needs:
1. **Speed, Determinism & Zero Token Cost (CI/CD Gates):** Every git commit must run instantly, reliably, and without network flakes or API bills.
2. **Real-User Cognitive & Visual Exploration (Quality Audits):** Real humans don't just execute predefined scripts; they explore, notice layout flaws, click unexpected buttons, and evaluate whether the AI coach is actually helpful.

To satisfy both needs, GoalCoach adopts a **three-tier hybrid architecture**:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                               GOALCOACH HYBRID TESTING SUITE                              │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  [Tier 1: Headless API Swarm]     [Tier 2A: Deterministic Playwright]   [Tier 2B: AI QA] │
│  - In-process FastAPI ASGI        - Real Chromium Browser               - Vision & LLM   │
│  - 4 Personas (10-100 turns/s)    - Clicks cards, modals, audio         - Exploratory UX │
│  - Bayesian DSR & DB WAL locks    - Headed (watch live) or Headless     - Human-like QA  │
│  - 100% Deterministic             - Zero console errors invariant       - On-demand CLI  │
│                                                                                          │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│               ▼                                 ▼                               ▼        │
│    Structured JSONL Logs                Browser Traces & Videos         Incident Reports │
│   (logs/goalcoach.jsonl)               (tests/e2e/test-results/)        (DuckDB Queries) │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

### Tier 1: In-Process Synthetic Learner Swarm (Backend Verification)
* **Execution:** Runs in-process via `httpx.ASGITransport` targeting `apps.api.main:create_app`.
* **Throughput:** 10–100 learning turns/second with zero TCP socket overhead.
* **Coverage:**
  * **Novice Persona:** Fast-path grading (<10ms), linear progression, prerequisite unlocks.
  * **Struggling Persona:** Deliberate grammatical errors, DSR stability decay, replanning flag triggers.
  * **Time-Warp Persona:** Simulated multi-day timestamp jumps ($\Delta t = 1, 7, 30\text{ days}$) testing retrievability decay.
  * **Adversarial Persona:** Fuzzing with malformed Unicode, 4000-character strings, boundary states.
  * **Concurrency:** Validates SQLite WAL write-lock contention across simultaneous learner sessions.

### Tier 2A: Deterministic Playwright Browser Agent (Frontend CI Backbone)
* **Execution:** Real browser engine via Python `pytest-playwright`.
* **Execution Modes:**
  * **Headed Mode (`pytest --headed`):** Opens a visible Chromium window on your desktop so you can watch the agent click through the application in real time.
  * **Headless Mode (`pytest`):** Runs silently at maximum speed in GitHub Actions or background scripts.
* **Coverage of Real UI Components:**
  * **DailyPlanView (`DailyPlanView.tsx`):** Reads lesson queue, checks completion status, clicks "Build today's plan" and "Start Study".
  * **TeachingAgentModal (`TeachingAgentModal.tsx`):** Answers multiple-choice and matching pair questions, verifies the green/red grading feedback banner, tests the tutor help request workflow (`onRequestHelp`), and closes modals.
  * **LearnerProfileDrawer (`LearnerProfileDrawer.tsx`):** Opens goal drawer, adjusts study minutes, saves changes, and verifies state persistence.
  * **Audio Synthesis:** Intercepts `/api/tts` network requests, ensuring HTTP 200 with valid `audio/mpeg` buffers.
  * **Zero-Tolerance Invariant:** Fails immediately if any uncaught JavaScript error, page error, or unhandled promise rejection appears in `console.error`.

### Tier 2B: Autonomous Exploratory AI Browser Agent (Cognitive/Visual QA)
* **Execution:** Standalone script (`scripts/ai_browser_evaluator.py`) powered by an LLM with vision.
* **How it works:**
  1. The agent boots the browser and navigates to the app.
  2. Takes DOM accessibility snapshots and screenshots.
  3. Acts as an unscripted student: reads what is on screen, tries to solve Mandarin exercises, asks clarifying questions, and explores edge-case navigation.
  4. Generates an executive UX & Visual Audit report noting layout glitches, confusing prompts, or unexpected coach responses.

### Tier 3: Telemetry Ingestion & DuckDB Anomaly Detection
* **Execution:** All backend requests and browser interactions emit structured events to `logs/goalcoach.jsonl`.
* **DuckDB Analyzer (`scripts/analyze_telemetry.py`):**
  * Queries the JSONL log directly without external database infrastructure.
  * Flags fast-path grading misses (`eval_path != 'fast_path'`).
  * Flags infinite replanning loops (`needs_replanning = True` > 3 consecutive turns).
  * Flags database slow queries (`duration_ms > 25.0`).
  * Emits `logs/test_incident_report.json` with trace IDs, query context, and error clusters.

---

## 2. Invariants & Isolation Rules

1. **Zero Database Pollution:** Tests never touch `./goalcoach.db`. All tests run against ephemeral SQLite databases created in `tmp_path` or `/tmp/` with copy-on-write content clones.
2. **Trace Correlation:** Every test injects `X-Test-Run-ID` and `X-Request-ID` headers, propagating via Python `contextvars` into SQL queries and application logs.
3. **Artifact Recording:** Every failed test run automatically saves Playwright video recordings, `.zip` action traces, and a JSON incident summary.

---

## 3. Target File Structure

```text
GoalCoach/
├── pyproject.toml                                  # Add playwright, pytest-playwright, duckdb
├── src/goalcoach/infrastructure/config.py          # Standardize default log_file_path to ./logs/goalcoach.jsonl
├── tests/
│   ├── conftest.py                                 # Ephemeral DB fixtures & curriculum seed verification
│   ├── e2e/
│   │   ├── conftest.py                             # Playwright browser fixtures, test server runner, console listeners
│   │   ├── test_ui_smoke.py                        # UI boot, plan render, and LearnerProfileDrawer test
│   │   └── test_learning_flow_e2e.py               # Complete lesson cycle (DailyPlan -> TeachingModal -> Audio -> Next)
│   └── harness/
│       ├── __init__.py
│       ├── synthetic_learner.py                    # 4 async personas (Novice, Struggling, TimeWarp, Adversarial)
│       └── test_synthetic_swarm.py                 # Multi-turn concurrent stress test
└── scripts/
    ├── analyze_telemetry.py                        # DuckDB log parser & anomaly reporter
    ├── ai_browser_evaluator.py                     # Autonomous AI exploratory browser tester
    └── run_agent_test_cycle.py                     # Single-command orchestrator for CI and local testing
```

---

## 4. Phased Implementation Roadmap

* **Phase 1: Environment & Dependency Provisioning**
  * Add dependencies (`playwright`, `pytest-playwright`, `duckdb`) to `pyproject.toml`.
  * Standardize log path to `logs/goalcoach.jsonl` in `config.py`.
  * Install Chromium binaries (`uv run python -m playwright install chromium`).

* **Phase 2: In-Process Synthetic Learner Swarm (Tier 1)**
  * Implement `SyntheticLearner` and the 4 personas in `tests/harness/synthetic_learner.py`.
  * Implement multi-turn concurrent test suite in `tests/harness/test_synthetic_swarm.py`.

* **Phase 3: Deterministic Playwright Browser Agent (Tier 2A)**
  * Implement `tests/e2e/conftest.py` with dynamic server startup and console error listeners.
  * Implement `tests/e2e/test_ui_smoke.py` and `tests/e2e/test_learning_flow_e2e.py`.
  * Support both `--headed` (watch live) and headless execution.

* **Phase 4: Telemetry Log Triaging (Tier 3)**
  * Implement `scripts/analyze_telemetry.py` using DuckDB.
  * Generate structured `logs/test_incident_report.json`.

* **Phase 5: Autonomous Exploratory AI Agent & Orchestrator (Tier 2B & Runner)**
  * Implement `scripts/ai_browser_evaluator.py` for autonomous cognitive UX testing.
  * Implement `scripts/run_agent_test_cycle.py` single-entrypoint runner.

---

## 5. How to Run the Testing Agent

### 1. Run the Full Unified Test Cycle (Tiers 1, 2, and 3)
Executes Tier 1 (Synthetic Swarm), boots ephemeral servers, executes Tier 2A (Playwright Browser Tests), and performs Tier 3 (DuckDB Telemetry Analysis):
```bash
uv run python scripts/run_agent_test_cycle.py
```

### 2. Watch the Agent Test Visually in a Real Browser (Headed Mode)
To launch a visible Chromium browser window on your desktop and observe the agent actively click buttons, solve exercises, and navigate:

* **Watch with paced human-speed clicks (Recommended):**
  ```bash
  uv run pytest tests/e2e/test_learning_flow_e2e.py --headed --slowmo 1000
  ```
  *(Inserts a 1-second pause between each action so you can follow along as the robot picks answers and receives feedback.)*

* **Watch the full test cycle in headed mode:**
  ```bash
  uv run python scripts/run_agent_test_cycle.py --headed
  ```

### 3. Run Backend Synthetic Swarm Tests Only (Tier 1)
High-throughput in-process ASGI testing simulating Novice, Struggling, Time-Warp, and Adversarial personas:
```bash
uv run pytest tests/harness/ -v
```

### 4. Run Deterministic Playwright Browser E2E Tests (Tier 2A)
Runs headless browser tests validating the UI boot, drawer interactions, exercise completion, and audio synthesis:
```bash
uv run pytest tests/e2e/ -v
```

### 5. Run Autonomous Exploratory AI Evaluator (Tier 2B)
Launches the exploratory QA agent to take DOM snapshots, capture screenshots in `logs/ai_eval/`, and audit UX:
```bash
uv run python scripts/ai_browser_evaluator.py
```

### 6. Run Telemetry Analysis on Existing Logs (Tier 3)
Parses `logs/goalcoach.jsonl` using DuckDB to flag fast-path misses, slow queries (>25ms), and generate `logs/test_incident_report.json`:
```bash
uv run python scripts/analyze_telemetry.py
```

---

## 6. Post-Test Lifecycle & Artifact Management

What happens after every test run:

| Artifact | Location | Lifecycle Behavior |
| :--- | :--- | :--- |
| **Test Database** | `/tmp/test_goalcoach_e2e_*.db` | **Ephemeral / Cleaned up:** Automatically created and destroyed per test session. Your main database (`goalcoach.db`) is never mutated. |
| **Screenshots** | `logs/ai_eval/*.png` | **Overwritten:** Updated on each run of the exploratory AI agent so only the latest visual state is preserved. |
| **Incident Report** | `logs/test_incident_report.json` | **Overwritten:** Re-generated on every DuckDB analysis run with the newest findings. |
| **Audit Logs** | `logs/goalcoach.jsonl` | **Appended:** Keeps an ongoing execution trace. To reset at any time, run `> logs/goalcoach.jsonl`. |