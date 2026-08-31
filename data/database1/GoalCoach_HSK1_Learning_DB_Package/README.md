# GoalCoach HSK1 Learning Content Database (SQLite)

## 1. Purpose

This is **Database #1: Structured Learning Content** for the GoalCoach HSK1 MVP.

It answers one main question:

> **What can GoalCoach teach?**

The database contains the structured learning material needed by the Goal Planning, Teaching, Exercise, Grading, and Progress components.

It intentionally does **not** contain learner-specific state such as mastery, retention, review schedules, or learning history. Those belong to a separate learner-state layer.

---

## 2. Files You Need

### Required for normal development

`goalcoach_hsk1_learning.db`

This is the ready-to-use SQLite database. It already contains the schema and seed data.

Put it in your project, for example:

```text
GoalCoach/
├── data/
│   └── goalcoach_hsk1_learning.db
├── src/
└── README.md
```

Your Python application can connect to this file directly.

### Recommended to keep in the GitHub repository

`goalcoach_hsk1_learning_db_sqlite.sql`

This contains the complete database schema and seed data.

It lets the team inspect the database structure, review changes, and rebuild the `.db` file if necessary.

### Documentation

`README.md`

This document explains the database structure and how other GoalCoach components should use it.

**Recommended:** keep all three files in the repository. For actually running the application, the `.db` file is the important one.

---

## 3. Why SQLite?

SQLite is a good fit for the current HSK1 MVP because:

- no separate database server is required;
- no database username, password, host, or port is required;
- the entire database is stored in one file;
- it is easy for all team members to run locally;
- the current dataset is small;
- Python has built-in SQLite support through `sqlite3`;
- it keeps the MVP architecture simple.

PostgreSQL can be introduced later if GoalCoach needs a production database server, higher concurrency, or more complex deployment.

Vector search is also unnecessary for this first structured content database.

---

## 4. Current Dataset

The database currently contains:

- **20 HSK1 MVP knowledge points**
- **21 teaching cards**
- **80 exercises**
- **18 prerequisite relationships**

The 20 knowledge points are a GoalCoach MVP teaching sequence. They should not be presented as an official HSK-prescribed 20-lesson sequence.

The learning experience is designed around short, focused interactions similar to common language-learning app patterns:

```text
Small Knowledge Point
        ↓
Short Teaching Card
        ↓
Recognition Exercise
        ↓
Controlled Practice
        ↓
Production
        ↓
Immediate Feedback
```

The content itself is GoalCoach-authored rather than copied from HelloChinese or Duolingo.

---

## 5. Database Structure

### `curriculum_concepts`

Stores the 20 HSK1 knowledge points.

Examples include:

- greetings;
- self-introduction;
- pronouns + 是;
- yes/no questions with 吗;
- questions with 什么;
- negation with 不;
- possession with 的;
- location with 在.

Main consumer:

**Goal Planning**

It helps answer:

> What concept should the learner study next?

---

### `concept_prerequisites`

Stores dependencies between concepts.

For example:

```text
Pronouns + 是
      ↓
Questions with 吗
```

The planner can use these relationships to avoid assigning a concept before its prerequisite knowledge is ready.

---

### `teaching_cards`

Stores short teaching content intended for the Teaching component and frontend.

A teaching card can contain:

- Chinese text;
- pinyin;
- English meaning;
- short explanation;
- example;
- mini-dialogue;
- teaching tip.

The cards are intentionally small enough to support a mobile-style, one-step-at-a-time learning experience.

---

### `exercises`

Stores the structured exercise bank.

Current exercise types include:

- meaning multiple choice;
- Chinese-to-English multiple choice;
- English-to-Chinese multiple choice;
- fill in the blank;
- sentence reordering;
- translation to Chinese;
- dialogue choice.

Important fields include:

`concept_id`

Identifies the knowledge point being practiced.

`answer`

Stores the expected answer as JSON.

`accepted_answers`

Stores alternative acceptable answers when appropriate.

`target_tokens`

Identifies the words or grammar elements the exercise is testing.

`error_tags`

Identifies the type of learner error that the exercise can diagnose or remediate.

`difficulty`

Provides a simple difficulty level that can later be used by the planner.

---

## 6. Database Views

Three views provide simple interfaces for the rest of GoalCoach.

### `v_concept_catalog`

Main consumer:

**Goal Planning**

Example:

```sql
SELECT *
FROM v_concept_catalog
ORDER BY sequence_no;
```

---

### `v_teaching_modules`

Main consumers:

**Teaching / Frontend**

Example:

```sql
SELECT *
FROM v_teaching_modules
WHERE concept_id = 'hsk1_c04'
ORDER BY card_order;
```

---

### `v_exercise_bank`

Main consumers:

**Exercise Service / Grader / Progress**

Example:

```sql
SELECT *
FROM v_exercise_bank
WHERE concept_id = 'hsk1_c04'
ORDER BY RANDOM()
LIMIT 3;
```

This retrieves three exercises for the `吗` knowledge point.

---

## 7. Connecting from Python

Python includes SQLite support, so no additional database package is required for the basic version.

```python
import sqlite3

conn = sqlite3.connect("data/goalcoach_hsk1_learning.db")
conn.row_factory = sqlite3.Row

exercises = conn.execute(
    '''
    SELECT *
    FROM v_exercise_bank
    WHERE concept_id = ?
    ORDER BY RANDOM()
    LIMIT 3
    ''',
    ("hsk1_c04",),
).fetchall()

for exercise in exercises:
    print(dict(exercise))
```

Use parameterized queries (`?`) rather than inserting user input directly into SQL strings.

---

## 8. JSON Fields

PostgreSQL-specific `JSONB` and array fields were replaced with JSON stored as text.

Examples include:

- `grammar_focus`
- `vocabulary_focus`
- `answer`
- `options`
- `accepted_answers`
- `target_tokens`
- `error_tags`
- `metadata`
- `payload`

Parse them in Python with `json.loads()`:

```python
import json

answer = json.loads(exercise["answer"])
target_tokens = json.loads(exercise["target_tokens"])
```

---

## 9. Selecting Remedial Exercises

Suppose the Progress component records that a learner repeatedly makes a `word_order` error.

SQLite can find matching exercises through its JSON functions:

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

This allows GoalCoach to select targeted remedial practice without vector search.

---

## 10. How GoalCoach Uses Database #1

```text
                  SQLite
                    │
       ┌────────────┼────────────┐
       │            │            │
       ▼            ▼            ▼
 Goal Planning   Teaching     Exercises
       │            │            │
       └────────────┼────────────┘
                    ▼
                  Learner
                    │
                    ▼
                  Grader
                    │
                    ▼
             Progress/Mastery
```

### Goal Planning

Reads:

- `curriculum_concepts`
- `concept_prerequisites`

Decides what should be learned next.

### Teaching

Reads:

- `teaching_cards`

Presents the selected concept.

### Exercise Service

Reads:

- `exercises`

Selects appropriate practice activities.

### Grader

For deterministic exercises, compares the learner response with:

- `answer`
- `accepted_answers`

Simple multiple-choice, fill-in, and reorder exercises therefore do not automatically require an LLM.

### Progress & Mastery

Consumes information such as:

- `concept_id`
- correctness;
- score;
- `target_tokens`;
- `error_tags`.

It can then update the learner's mastery, retention, error profile, and review schedule in the future learner-state layer.

---

## 11. Rebuilding the Database

If the `.db` file needs to be recreated, use the SQL file:

```bash
sqlite3 goalcoach_hsk1_learning.db < goalcoach_hsk1_learning_db_sqlite.sql
```

You can then inspect the database:

```bash
sqlite3 goalcoach_hsk1_learning.db
```

Inside SQLite:

```sql
.tables
```

You should see the core tables:

```text
curriculum_concepts
concept_prerequisites
teaching_cards
exercises
```

Test the data:

```sql
SELECT COUNT(*) FROM curriculum_concepts;
SELECT COUNT(*) FROM exercises;
```

Expected values:

```text
20
80
```

Exit:

```text
.quit
```

---

## 12. Current Architectural Boundary

Database #1 is the **learning-content layer**.

```text
Database #1
"What can we teach?"
        │
        ▼
Goal Planning
"What should this learner learn next?"
        │
        ▼
Teaching
"How should we present it?"
        │
        ▼
Grading
"How well did the learner answer?"
        │
        ▼
Learner State
"What does this learner currently know?"
```

Keeping these responsibilities separate makes it easier to connect the content database to the later Goal Planning, Teaching, Grading, and Progress modules without turning the content database into an agent or learner-memory system.
