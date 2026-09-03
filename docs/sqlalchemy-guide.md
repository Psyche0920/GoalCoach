# SQLAlchemy Guide: Connecting to SQL When the DB Is Ready

## What is SQLAlchemy?

SQLAlchemy is Python's most popular **ORM** (Object-Relational Mapper). It lets you talk to a
relational database (SQLite, PostgreSQL, MySQL, etc.) using **Python classes and objects instead
of raw SQL strings**.

Two layers, working together:

| Layer | What it does | Analogy |
|-------|--------------|---------|
| **Core** | SQL expression language (`select`, `insert`, `where`…) | Building queries in Python |
| **ORM** | Maps Python classes ↔ database tables | Columns become attributes on objects |

You write Python, SQLAlchemy translates it into database-specific SQL for you. This means the
same code works whether the database is SQLite (local dev) or PostgreSQL (production).

---

## How the pieces fit together

```
Your code  →  Session  →  Engine  →  Database
                 │                      │
        (holds a connection)    (knows the DB URL)
```

- **Engine** — one per database. Knows the URL (`sqlite:///...`, `postgresql://user:pw@host/db`).
- **Session** — what you actually use to query/save. A session wraps one engine connection.
- **Model classes** — Python classes that map 1-to-1 with your DB tables.
- **Repository** — a class that wraps common queries so the rest of the app never touches SQL.

---

## The setup already in this project

Everything you need is in `src/goalcoach/infrastructure/persistence/`:

```
persistence/
├── database.py      # creates Engine + Session factory from a DB URL
├── models.py        # the table definitions (SQLAlchemy model classes)
└── repositories.py  # ready-to-use query helpers (ContentRepository)
```

### 1. `database.py` — engine + session factory

`create_session_factory(database_url)` turns a connection string into a session factory.
It even auto-enables SQLite foreign keys for you.

```python
from goalcoach.infrastructure.persistence.database import create_session_factory

factory = create_session_factory("sqlite:///./goalcoach.db")
```

> The URL usually comes from `Settings().database_url` (`.env`), **not** hard-coded.

### 2. `models.py` — your table definitions

Each class = one table. Each `Mapped[...]` attribute = one column. Existing tables:

- `CurriculumConcept` — one HSK concept/skill (the main entity)
- `TeachingCard` — teaching cards that belong to a concept
- `ContentExercise` — exercises that belong to a concept
- `ConceptPrerequisite` — "must learn A before B" links between concepts

Relationships (`relationship(...)`) let you navigate from one table to another, e.g.
`concept.exercises` gives you that concept's exercises.

### 3. `repositories.py` — ready-made queries

`ContentRepository` already gives you working queries against the content DB:

```python
from goalcoach.infrastructure.persistence.database import create_session_factory
from goalcoach.infrastructure.persistence.repositories import ContentRepository

factory = create_session_factory("sqlite:///./data/database1/goalcoach_hsk1_learning.db")
repo = ContentRepository(factory)

concepts = repo.list_concepts(hsk_level=1)          # active HSK-1 concepts
cards    = repo.get_teaching_cards("some-concept-id")
exercises = repo.get_exercises("some-concept-id", limit=3)
remedial = repo.get_remedial_exercises("word_order", limit=5)
```

---

## Writing your own query (the basics)

Use a `Session` and the `select()` expression builder:

```python
from sqlalchemy import select
from goalcoach.infrastructure.persistence.models import CurriculumConcept

with factory() as session:                       # open a session (auto-closes)
    result = session.scalars(select(CurriculumConcept))   # SELECT *
    rows = list(result)                          # ORM objects, ready to use
```

Filter / order / limit:

```python
stmt = (
    select(CurriculumConcept)
    .where(CurriculumConcept.hsk_level == 1, CurriculumConcept.is_active.is_(True))
    .order_by(CurriculumConcept.sequence_no)
    .limit(10)
)
with factory() as session:
    rows = list(session.scalars(stmt))
```

Insert a new row:

```python
from goalcoach.infrastructure.persistence.models import CurriculumConcept

with factory() as session:
    session.add(CurriculumConcept(
        concept_id="c-001",
        hsk_level=1,
        sequence_no=1,
        slug="greetings",
        title_zh="问候",
        title_en="Greetings",
        concept_type="communicative",
        # ... other required fields
    ))
    session.commit()   # you MUST commit for writes to persist
```

---

## When your coworker finishes the SQL

The good news: **you don't change any code to "connect" — you just point at the finished database.**

1. **Confirm the schema matches the models.** If your coworker's schema differs from
   `models.py` (different table/column names), update `models.py` to match the real schema.
   Column order doesn't matter — SQLAlchemy matches by name.

2. **Point the app at the finished DB** by setting the URL in `.env`:
   ```
   GOALCOACH_DATABASE_URL=postgresql://user:pass@host:5432/goalcoach
   ```

3. **Use `create_session_factory(url)` + a repository** exactly as shown above. The rest of
   the code keeps working unchanged because it talks to the repository, not the database.

> If the tables aren't created yet, you can create them from the models with
> `Base.metadata.create_all(engine)` — but prefer importing a real schema/dump if one exists.

---

## How the app currently uses it (so you can match the style)

The FastAPI endpoints in `apps/api/main.py` are still stubs (`501 Not Implemented`). When you
wire them up, the pattern is:

```python
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.persistence.database import create_session_factory
from goalcoach.infrastructure.persistence.repositories import ContentRepository

settings = Settings()
factory = create_session_factory(settings.content_database_url)
repo = ContentRepository(factory)
```

Then call `repo.…` inside your endpoint and return the result.

---

## Common commands / quick reference

```bash
# Run the tests (the API smoke tests exercise the app in-memory)
.venv/bin/python -m pytest tests/ -v
```

```python
from sqlalchemy import select, func      # select + aggregate helpers
from sqlalchemy.orm import Session       # session typing
```

---

## Checklist before wiring endpoints to the DB

- [ ] Confirm the target DB is reachable (run a trivial `select`)
- [ ] Confirm `models.py` column names match the real schema
- [ ] Use `Settings().database_url` / `Settings().content_database_url`, don't hard-code
  the URL (keeps prod-escalation simple)
- [ ] Wrap each DB access in the repository pattern (no raw SQL in the API layer)
- [ ] `commit()` after any writes
- [ ] Test against SQLite (dev) and the real DB before merging
