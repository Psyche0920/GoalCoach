# Contributing to GoalCoach

Thank you for your interest in contributing to GoalCoach! GoalCoach is an adaptive, closed state-driven agentic learning system designed for Chinese-as-a-second-language learners (HSK 1 MVP).

We welcome contributions from engineers, educators, and researchers. To maintain a rigorous enterprise engineering standard, please review these guidelines before submitting code.

---

## 1. Architectural Invariants

Before writing code, understand the core constraints of the system:
1. **State-Driven, Not Conversation-Driven**: User interactions mutate persistent relational state in SQLite. Conversational chat history does not represent learner mastery.
2. **Deterministic Governance**: Event routing, mastery calculations (40/40/20 reducer), retention decay, spaced review intervals, and prerequisite enforcement remain 100% pure deterministic Python.
3. **No Sequential Agent Chaining**: Never execute Planner $\rightarrow$ Retrieval $\rightarrow$ Tutor $\rightarrow$ Grader sequentially for a single user turn. One turn must invoke at most one reasoning agent or evaluator.
4. **Curriculum Grounding**: Content is grounded in curated HSK 1 curriculum records (Database #1). Never let models invent ungrounded concept identifiers or hallucinate curriculum relationships.
5. **Strict Schema Boundaries**: All LLM inputs and outputs are governed by Pydantic v2 schemas (`PlanUpdate`, `TeachingAction`, `GradingResult`).

---

## 2. Prerequisites & Toolchain

- **Python**: `3.12+` (minimum `3.11`)
- **Package & Dependency Manager**: [Astral `uv`](https://docs.astral.sh/uv/) (v0.4+)
- **Database Engine**: SQLite 3 (with WAL mode support)
- **Node.js**: `v18+` (for React / Vite frontend development under `apps/web/`)

---

## 3. Local Development Setup

### 3.1 Clone and Install Dependencies

```bash
git clone https://github.com/Psyche0920/GoalCoach.git
cd GoalCoach

# Create venv and install all dependencies (including dev, ai, web, and retrieval extras)
uv sync --all-extras
```

### 3.2 Initialize Databases

GoalCoach utilizes dual SQLite databases:
- **Database #1 (`data/database1/goalcoach_hsk1_learning.db`)**: Static curated curriculum concepts, examples, and prerequisites.
- **Database #2 (`goalcoach.db`)**: Dynamic learner state, masteries, error profiles, and daily plans (WAL mode).

Bootstrap Database #1 from the SQL package:
```bash
mkdir -p data/database1
sqlite3 data/database1/goalcoach_hsk1_learning.db < GoalCoach_HSK1_Learning_DB_Package/data/goalcoach_hsk1_learning_db_sqlite.sql
```

*(Note: Pytest includes an autouse fixture in `tests/conftest.py` that automatically initializes this database if missing during test runs).*

### 3.3 Configure Environment Variables

Copy the example configuration file:
```bash
cp .env.example .env
```

Configure your models in `.env`:
```ini
GOALCOACH_ENVIRONMENT=development
GOALCOACH_DATABASE_URL=sqlite:///./goalcoach.db
GOALCOACH_CONTENT_DATABASE_URL=sqlite:///./data/database1/goalcoach_hsk1_learning.db

# Primary Model (Hosted via OpenRouter or OpenAI-compatible endpoint)
GOALCOACH_LLM_BASE_URL=https://openrouter.ai/api/v1
GOALCOACH_LLM_API_KEY=your-openrouter-api-key
GOALCOACH_LLM_MODEL="inclusionai/ling-3.0-flash-fin"

# Fallback Model (Local via Ollama)
GOALCOACH_ENABLE_OLLAMA_FALLBACK=false
GOALCOACH_FALLBACK_LLM_BASE_URL=http://localhost:11434/v1
GOALCOACH_FALLBACK_LLM_MODEL=hf.co/unsloth/gemma-4-E4B-it-GGUF:Q4_K_M
# Alternative local model: hf.co/unsloth/gemma-4-E2B-it-GGUF:Q4_K_M
# Note: More models for testing will be added and evaluated later.
```

---

## 4. Code Quality & Verification

Every pull request must pass formatting, linting, and both unit and integration test suites.

### 4.1 Ruff Linting and Formatting

We enforce strict linting and formatting via Ruff:

```bash
# Check code style and common lint issues
uv run ruff check src/ apps/ tests/

# Automatically fix lint issues where supported
uv run ruff check --fix src/ apps/ tests/

# Check formatting compliance (0 diffs required)
uv run ruff format --check src/ apps/ tests/

# Format all codebase files
uv run ruff format src/ apps/ tests/
```

### 4.2 Running Tests

Always execute the test suite before submitting changes:

```bash
# 1. Fast Unit Tests (domain math, reducers, pure logic)
uv run pytest tests/unit/ -v

# 2. Integration Tests (closed loop, remediation, persistence, vector retrieval)
GOALCOACH_ENVIRONMENT="testing" \
GOALCOACH_LLM_API_KEY="ci-mock-token" \
GOALCOACH_ENABLE_VECTOR_RETRIEVAL="true" \
uv run pytest tests/integration/ -v

# 3. Complete Test Run
uv run pytest -v
```

All 100 tests across unit and integration suites must pass with zero errors.

---

## 5. Development Workflows

### 5.1 Running the API Server

```bash
uv run uvicorn apps.api.main:app --reload --port 8000
```
Interactive API documentation will be available at `http://localhost:8000/docs`.

### 5.2 Running the Interactive CLI Terminal Harness

To test teaching and grading directly in the terminal:
```bash
uv run python -m src.goalcoach.agents.terminal_harness
```

### 5.3 Running the React / Vite Frontend

```bash
cd apps/web
npm install
npm run dev
```

---

## 6. Contribution Standards & Git Workflow

### 6.1 Branch Naming Convention

Create feature branches off `main`:
- `feature/<feature-name>` (e.g., `feature/spaced-repetition-tuning`)
- `fix/<bug-name>` (e.g., `fix/remediation-exercise-rotation`)
- `docs/<doc-name>` (e.g., `docs/update-architecture-diagrams`)
- `chore/<chore-name>` (e.g., `chore/bump-dependencies`)

### 6.2 Conventional Commits

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat(...)`: A new feature or capability
- `fix(...)`: A bug fix
- `docs(...)`: Documentation only changes
- `style(...)`: Formatting, whitespace, or lint fixes without logic change
- `refactor(...)`: Code changes that neither fix a bug nor add a feature
- `test(...)`: Adding or updating tests
- `chore(...)`: Dependency updates, build configs, or maintenance

*Examples:*
- `feat(agents): implement dynamic exercise rotation for remediation`
- `fix(reducer): prevent occurrences decrement validation error in ErrorRecord`
- `docs(readme): modernize setup guide and add architectural dataflow`

### 6.3 Pull Request Process

1. Ensure `uv lock --check` succeeds.
2. Run `uv run ruff check src/ apps/ tests/` and `uv run ruff format --check src/ apps/ tests/`.
3. Run the full pytest suite (`tests/unit/` and `tests/integration/`).
4. Submit your PR against the `main` branch with:
   - A clear summary of the change.
   - The rationale and architectural impact.
   - Verification steps or automated test proof.
5. Ensure all GitHub Actions CI pipeline checks pass.
