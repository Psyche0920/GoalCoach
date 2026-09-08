# GoalCoach — Database & API Access Guide

## Architecture Overview

GoalCoach uses **SQLAlchemy ORM** with two **SQLite** databases:

| Database | Path | Purpose |
|---|---|---|
| Learner DB | `goalcoach.db` | Stores learner state snapshots (JSON) |
| Content DB | `data/database1/goalcoach_hsk1_learning.db` | HSK curriculum, teaching cards, exercises, prerequisites |

The **FastAPI** server exposes REST endpoints that read/write through repository classes.

---

## 1. Environment Setup

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Key variables in `.env`:

```
GOALCOACH_ENVIRONMENT=development
GOALCOACH_DATABASE_URL=sqlite:///./goalcoach.db
GOALCOACH_CONTENT_DATABASE_URL=sqlite:///./data/database1/goalcoach_hsk1_learning.db
```

---

## 2. Starting the API Server

```bash
uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API docs are available at `http://localhost:8000/docs`.

---

## 3. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/learners/{learner_id}` | Get a learner's state |
| `POST` | `/api/v1/learners/{learner_id}/plans` | Generate a daily plan |
| `POST` | `/api/v1/answers` | Submit an exercise answer |

---

## 4. Accessing the Database via API

### Health Check

```bash
curl http://localhost:8000/health
```

Response:

```json
{"status": "ok"}
```

### Get Learner State

```bash
curl http://localhost:8000/api/v1/learners/{uuid}
```

Returns the full `LearnerState` model including:

- `learner_id` — UUID
- `current_level` — HSK level
- `mastered_concepts` — list of concept IDs
- `performance_history` — past results
- `updated_at` — last save timestamp

**404** if the learner does not exist.

### Generate Daily Plan

```bash
curl -X POST http://localhost:8000/api/v1/learners/{uuid}/plans
```

Returns a `DailyPlan` with recommended concepts, estimated duration, and exercise list.

### Submit Answer

```bash
curl -X POST http://localhost:8000/api/v1/answers \
  -H "Content-Type: application/json" \
  -d '{"exercise_id": "...", "learner_id": "...", "user_answer": "..."}'
```

> Currently returns **501 Not Implemented** (learning loop not yet connected).

---

## 5. Accessing the Database Directly (Python)

### Using the Session Factory

```python
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.persistence.database import (
    create_session_factory,
    create_learner_schema,
)

settings = Settings()
session_factory = create_session_factory(settings.database_url)
create_learner_schema(session_factory)
```

### Querying Learner States

```python
from sqlalchemy import select
from goalcoach.infrastructure.persistence.models import LearnerStateRecord

with session_factory() as session:
    record = session.get(LearnerStateRecord, "some-uuid")
    if record:
        print(record.state_json)
        print(record.updated_at)
```

### Querying Content (HSK Curriculum)

```python
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.persistence.database import create_session_factory
from goalcoach.infrastructure.persistence.repositories import ContentRepository

settings = Settings()
content_sf = create_session_factory(settings.content_database_url)
repo = ContentRepository(content_sf)

# List HSK1 concepts
concepts = repo.list_concepts(hsk_level=1)

# Get teaching cards for a concept
cards = repo.get_teaching_cards("concept_001")

# Get exercises
exercises = repo.get_exercises("concept_001", limit=3)

# Get prerequisite map
prereqs = repo.get_prerequisites()
```

---

## 6. Database Schema Reference

### `learner_states`

| Column | Type | Description |
|---|---|---|
| `learner_id` | `VARCHAR(36)` PK | Learner UUID |
| `state_json` | `JSON` | Full `LearnerState` snapshot |
| `updated_at` | `DATETIME` | Last update timestamp |

### `curriculum_concepts`

| Column | Type | Description |
|---|---|---|
| `concept_id` | `VARCHAR` PK | Unique concept ID |
| `hsk_level` | `INTEGER` | HSK level (1, 2, …) |
| `sequence_no` | `INTEGER` UNIQUE | Ordering index |
| `slug` | `VARCHAR` UNIQUE | URL-safe name |
| `title_zh` | `VARCHAR` | Chinese title |
| `title_en` | `VARCHAR` | English title |
| `concept_type` | `VARCHAR` | e.g. "grammar", "vocabulary" |
| `communicative_goal` | `TEXT` | Learning objective |
| `grammar_focus` | `JSON` | Grammar points list |
| `vocabulary_focus` | `JSON` | Vocabulary words list |
| `difficulty` | `INTEGER` | 1–5 scale |
| `estimated_minutes` | `INTEGER` | Time estimate |
| `is_active` | `BOOLEAN` | Whether active |
| `metadata_json` | `JSON` | Extra metadata |

### `teaching_cards`

| Column | Type | Description |
|---|---|---|
| `card_id` | `INTEGER` PK | Auto-increment |
| `concept_id` | `VARCHAR` FK | Links to `curriculum_concepts` |
| `card_order` | `INTEGER` | Display order |
| `card_type` | `VARCHAR` | Card type |
| `prompt_zh` | `TEXT` | Chinese prompt |
| `pinyin` | `TEXT` | Pinyin |
| `meaning_en` | `TEXT` | English meaning |
| `explanation_en` | `TEXT` | Explanation |
| `example_zh` | `TEXT` | Chinese example |
| `example_pinyin` | `TEXT` | Example pinyin |
| `example_en` | `TEXT` | Example translation |
| `payload` | `JSON` | Extra data |

### `exercises`

| Column | Type | Description |
|---|---|---|
| `exercise_id` | `VARCHAR` PK | Exercise ID |
| `concept_id` | `VARCHAR` FK | Links to concept |
| `exercise_order` | `INTEGER` | Ordering |
| `exercise_type` | `VARCHAR` | e.g. "multiple_choice", "fill_blank" |
| `prompt` | `TEXT` | Question text |
| `answer` | `JSON` | Correct answer |
| `options` | `JSON` | Answer options (nullable) |
| `accepted_answers` | `JSON` | Valid alternatives |
| `explanation` | `TEXT` | Why the answer is correct |
| `target_tokens` | `JSON` | Key vocabulary |
| `error_tags` | `JSON` | Tags for remedial matching |
| `difficulty` | `INTEGER` | 1–5 scale |
| `points` | `INTEGER` | Score value |

### `concept_prerequisites`

| Column | Type | Description |
|---|---|---|
| `concept_id` | `VARCHAR` PK FK | Target concept |
| `prerequisite_id` | `VARCHAR` PK FK | Required concept |

---

## 7. Key Source Files

| File | Purpose |
|---|---|
| `apps/api/main.py` | FastAPI app, routes, lifespan |
| `src/goalcoach/infrastructure/config.py` | Settings from `.env` |
| `src/goalcoach/infrastructure/persistence/database.py` | Engine, session factory, schema creation |
| `src/goalcoach/infrastructure/persistence/models.py` | SQLAlchemy ORM models |
| `src/goalcoach/infrastructure/persistence/repositories.py` | `ContentRepository`, `SqlAlchemyLearnerRepository` |
| `src/goalcoach/domain/models.py` | Pydantic domain models |

---

## 8. Common Tasks

### Reset the Learner Database

```bash
rm goalcoach.db
# Schema is auto-created on next server start via create_learner_schema()
```

### Backup Content Database

```bash
cp data/database1/goalcoach_hsk1_learning.db data/database1/goalcoach_hsk1_learning.db.bak
```

### Inspect SQLite Directly

```bash
sqlite3 goalcoach.db "SELECT * FROM learner_states;"
sqlite3 data/database1/goalcoach_hsk1_learning.db "SELECT concept_id, title_zh, title_en FROM curriculum_concepts;"
```

### Run Tests

```bash
uv run pytest
```
