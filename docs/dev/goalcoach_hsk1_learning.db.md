# `goalcoach_hsk1_learning.db`

## Overview

`goalcoach_hsk1_learning.db` is the authoritative structured learning-content database for the
GoalCoach HSK1 MVP. It answers one bounded question:

> What learning content can GoalCoach teach and practise?

The database contains curriculum concepts, prerequisite relationships, teaching cards, and
exercises. It does not contain learner-specific state such as goals, mastery scores, retention,
review schedules, errors, plans, or session history. Those concerns belong to the learner-state
database and domain layer.

Keeping content and learner state separate prevents static curriculum data from becoming coupled
to individual users, and allows the content catalogue to be reviewed, rebuilt, and versioned
independently.

## Canonical Location and Supporting Artifacts

The application uses this database by default:

```text
data/database1/goalcoach_hsk1_learning.db
```

This path matches the default setting in `src/goalcoach/infrastructure/config.py`:

```text
sqlite:///./data/database1/goalcoach_hsk1_learning.db
```

The repository also contains the original delivery package:

```text
data/database1/GoalCoach_HSK1_Learning_DB_Package.zip
data/database1/GoalCoach_HSK1_Learning_DB_Package/data/goalcoach_hsk1_learning.db
data/database1/GoalCoach_HSK1_Learning_DB_Package/data/goalcoach_hsk1_learning_db_sqlite.sql
```

Use `data/database1/goalcoach_hsk1_learning.db` at runtime. Treat the SQL file as the reviewable
schema-and-seed source used to rebuild the database. The packaged `.db` file is a delivery artifact,
not a second runtime database.

## Technology Choice

SQLite is appropriate for the current MVP because the content dataset is small, read-heavy, and
distributed with the application. It requires no database server, credentials, port allocation, or
local provisioning. SQLAlchemy provides the application-facing persistence abstraction, so callers
do not need to depend directly on SQLite APIs.

A server database may become appropriate if deployment later requires concurrent content editing,
centralized administration, or larger production workloads. That decision should be driven by
measured requirements rather than introduced into the MVP pre-emptively.

Vector search is not required for known concept IDs, curriculum order, prerequisite traversal, or
error-tag filtering. Structured relational queries are more predictable for those operations.

## Dataset Snapshot

The checked-in database currently contains:

| Object | Count | Purpose |
|---|---:|---|
| `curriculum_concepts` | 20 | Ordered HSK1 MVP curriculum concepts |
| `concept_prerequisites` | 18 | Directed prerequisite relationships |
| `teaching_cards` | 21 | Small instructional units |
| `exercises` | 80 | Structured practice and assessment items |

The 20 concepts form a GoalCoach-authored MVP sequence. They must not be described as an official
HSK-prescribed 20-lesson curriculum. The learning content is original GoalCoach material and should
not be represented as copied from a commercial learning product.

## Schema

### `curriculum_concepts`

This is the curriculum catalogue and the parent table for teaching cards, exercises, and
prerequisite relationships.

Important fields include:

- `concept_id`: stable external identifier, for example `hsk1_c04`;
- `sequence_no`: deterministic default curriculum order from 1 through 20;
- `title_zh` and `title_en`: learner- and developer-facing names;
- `concept_type`: `communication`, `grammar`, `vocabulary`, or `mixed`;
- `communicative_goal`: the practical learning outcome;
- `grammar_focus` and `vocabulary_focus`: JSON arrays stored as text;
- `difficulty`: integer from 1 through 5;
- `estimated_minutes`: expected learning time for the concept;
- `is_active`: controls whether repositories and views expose the concept;
- `metadata`: extensible JSON object.

The sequence is a deterministic fallback. Adaptive planning may filter or rank eligible concepts
using prerequisites and learner state before using `sequence_no` as a tie-breaker.

### `concept_prerequisites`

This table represents directed curriculum dependencies:

```text
prerequisite_id ──must precede──> concept_id
```

Its composite primary key prevents duplicate relationships, and its check constraint prevents a
concept from depending directly on itself. Application logic should still guard against longer
cycles when prerequisite data is edited.

### `teaching_cards`

Teaching cards are short presentation units associated with one curriculum concept. Supported card
types are:

- `goal`;
- `vocab`;
- `grammar`;
- `example`;
- `tip`;
- `mini_dialogue`.

Cards may include Chinese text, pinyin, English meaning, explanations, examples, and structured JSON
payloads. The `(concept_id, card_order)` constraint guarantees a stable order within each concept.

### `exercises`

The exercise bank supports:

- `meaning_mcq`;
- `zh_to_en_mcq`;
- `en_to_zh_mcq`;
- `fill_blank`;
- `reorder`;
- `translate_to_zh`;
- `dialogue_choice`.

Important fields include:

- `answer`: canonical answer encoded as JSON;
- `accepted_answers`: alternative valid answers;
- `options`: choices for applicable exercise types;
- `target_tokens`: vocabulary or grammar elements being assessed;
- `error_tags`: structured tags used to select remedial exercises;
- `difficulty`: integer from 1 through 5;
- `points`: positive scoring weight;
- `metadata`: extensible JSON object.

The `(concept_id, exercise_order)` constraint provides deterministic ordering when random selection
is disabled.

## Read Views

Three views expose stable, active-content projections:

| View | Primary consumers | Purpose |
|---|---|---|
| `v_concept_catalog` | Goal Planning | Active concepts in curriculum order |
| `v_teaching_modules` | Teaching and UI | Concepts joined to ordered teaching cards |
| `v_exercise_bank` | Exercise selection, grading, progress | Active exercises with concept context |

Example queries:

```sql
SELECT *
FROM v_concept_catalog
ORDER BY sequence_no;

SELECT *
FROM v_teaching_modules
WHERE concept_id = 'hsk1_c04'
ORDER BY card_order;

SELECT *
FROM v_exercise_bank
WHERE concept_id = 'hsk1_c04'
ORDER BY exercise_order
LIMIT 3;
```

Use deterministic ordering in tests. Random ordering is suitable only when the caller explicitly
wants exercise variation.

## Application Access

Application code should use `ContentRepository` rather than open SQLite connections or construct SQL
strings directly:

```python
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.persistence import (
    ContentRepository,
    create_session_factory,
)

settings = Settings()
session_factory = create_session_factory(settings.content_database_url)
repository = ContentRepository(session_factory)

concepts = repository.list_concepts(hsk_level=1)
cards = repository.get_teaching_cards("hsk1_c04")
exercises = repository.get_exercises(
    "hsk1_c04",
    limit=3,
    randomize=False,
)
remedial = repository.get_remedial_exercises("word_order", limit=5)
```

The repository uses parameterized SQLAlchemy expressions and automatically excludes inactive
concepts. Callers should pass values through repository methods rather than interpolate SQL.

## JSON Storage

SQLite stores the following structured fields as JSON text, while SQLAlchemy maps them to Python
lists or dictionaries:

- `grammar_focus`;
- `vocabulary_focus`;
- `metadata`;
- `payload`;
- `answer`;
- `options`;
- `accepted_answers`;
- `target_tokens`;
- `error_tags`.

For example:

```python
exercise = repository.get_exercises("hsk1_c04", limit=1)[0]
answer = exercise.answer
target_tokens = exercise.target_tokens
```

SQLite JSON functions support structured error-tag filtering without vector search:

```sql
SELECT *
FROM v_exercise_bank
WHERE EXISTS (
    SELECT 1
    FROM json_each(error_tags)
    WHERE value = 'word_order'
)
ORDER BY RANDOM()
LIMIT 5;
```

The application-level equivalent is:

```python
remedial = repository.get_remedial_exercises("word_order", limit=5)
```

## Component Responsibilities

```text
goalcoach_hsk1_learning.db
          │
          ├── curriculum concepts + prerequisites ──> Goal Planning
          ├── teaching cards ───────────────────────> Teaching / UI
          └── exercises + answer metadata ──────────> Exercise selection / Grading
                                                        │
                                                        ▼
                                                   Progress update
                                                        │
                                                        ▼
                                            Separate learner-state storage
```

- Goal Planning selects eligible concepts; it does not edit curriculum content.
- Teaching presents cards associated with the selected concept.
- Exercise selection retrieves appropriate practice activities.
- Deterministic grading may compare responses with `answer` and `accepted_answers`.
- Progress processing consumes results and error tags, then updates learner state elsewhere.

## Rebuilding the Database

The SQL source uses `CREATE ... IF NOT EXISTS` and `ON CONFLICT ... DO NOTHING`. Running it against
an existing database adds missing objects or seed rows but does not overwrite existing rows. To
create a clean database, first preserve or move the current file, then run from the repository root:

```bash
sqlite3 data/database1/goalcoach_hsk1_learning.db \
  < data/database1/GoalCoach_HSK1_Learning_DB_Package/data/goalcoach_hsk1_learning_db_sqlite.sql
```

Do not delete the current database until any intentional changes are represented in the SQL source
or otherwise backed up. Review the resulting Git diff rather than treating the binary database as
the only source of truth.

Verify the rebuilt dataset:

```bash
sqlite3 data/database1/goalcoach_hsk1_learning.db \
  "SELECT 'concepts', COUNT(*) FROM curriculum_concepts
   UNION ALL
   SELECT 'prerequisites', COUNT(*) FROM concept_prerequisites
   UNION ALL
   SELECT 'cards', COUNT(*) FROM teaching_cards
   UNION ALL
   SELECT 'exercises', COUNT(*) FROM exercises;"
```

Expected counts are 20 concepts, 18 prerequisites, 21 cards, and 80 exercises.

## Validation

Run the content-repository integration tests from the repository root:

```bash
pytest tests/integration/test_content_repository.py -q
```

For database changes, validation should cover:

- schema creation from the SQL source;
- expected row counts;
- foreign-key integrity;
- valid JSON in all structured fields;
- repository queries with deterministic ordering;
- inactive-content filtering;
- remedial lookup by error tag.

Any schema change must be reviewed together with the SQLAlchemy persistence models and repository
queries. A binary `.db` update without a matching SQL source and integration-test evidence is not a
complete database change.
