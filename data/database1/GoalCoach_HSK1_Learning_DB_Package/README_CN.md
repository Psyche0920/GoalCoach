# GoalCoach HSK1 学习内容数据库（SQLite）

## 为什么从 PostgreSQL 改成 SQLite

对当前 HSK1 MVP，SQLite 更合适：不需要单独启动数据库服务器，不需要用户名、端口和数据库服务配置；数据库就是一个 `.db` 文件，三个人 clone 项目后即可运行。

当前数据量只有 20 个知识点、教学卡和 80 道练习，SQLite 完全足够。后续如果需要多用户并发、独立数据库服务或更复杂的生产部署，再迁移 PostgreSQL。

## 文件

- `goalcoach_hsk1_learning.db`：已经建好并填充数据，可直接接入 Python。
- `goalcoach_hsk1_learning_db_sqlite.sql`：完整 schema + seed data，可重新生成数据库。

## 表

- `curriculum_concepts`：20 个 HSK1 MVP 知识点。
- `teaching_cards`：短教学卡。
- `exercises`：80 道结构化练习。
- `concept_prerequisites`：知识点前置关系。

## Views

- `v_concept_catalog`：给 Goal Planning 使用。
- `v_teaching_modules`：给 Teaching / UI 使用。
- `v_exercise_bank`：给 Exercise Service / Grader 使用。

## Python 使用 SQLAlchemy 连接

```python
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.persistence import (
    ContentRepository,
    create_session_factory,
)

settings = Settings()
session_factory = create_session_factory(settings.content_database_url)
repository = ContentRepository(session_factory)

concepts = repository.list_concepts()
cards = repository.get_teaching_cards("hsk1_c04")
exercises = repository.get_exercises("hsk1_c04", limit=3)
```

## JSON 字段

SQLite 没有 PostgreSQL 的 `JSONB` 和 `TEXT[]` 类型，因此这些字段以 JSON 字符串存储：

- `grammar_focus`
- `vocabulary_focus`
- `answer`
- `options`
- `accepted_answers`
- `target_tokens`
- `error_tags`
- `metadata`
- `payload`

SQLAlchemy 的 `JSON` 类型会自动把这些字段转换为 Python 对象：

```python
answer = exercises[0].answer
target_tokens = exercises[0].target_tokens
```

## 根据错误标签找补救题

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

## 当前职责

Database #1 只回答：

**GoalCoach 有什么内容可以教？**

它暂时不保存 LearnerState、Mastery、Retention、Review Schedule。那些属于后面的学习者状态层。
