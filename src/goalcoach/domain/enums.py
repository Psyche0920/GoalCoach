"""Domain enumerations for learning plan items, plan execution statuses, and content retrieval modes."""

from enum import StrEnum

# `StrEnum` 同时具备字符串和枚举的特性：
# 1. 代码内部使用受约束的枚举成员，避免到处传递容易拼错的裸字符串。
# 2. 对外序列化时仍可得到 `"review"`、`"active"` 这类清晰的字符串值。
# 3. Pydantic 和 FastAPI 可以据此校验输入；不在枚举中的值会被拒绝。


class PlanItemKind(StrEnum):
    """Classification of an individual item in a learner's daily plan."""

    # 复习项目：概念已经学过，并且根据间隔复习时间表当前需要复习。
    REVIEW = "review"

    # 补救项目：概念已经接触过，但掌握分数偏低，需要针对性强化。
    REMEDIAL = "remedial"

    # 新学项目：学习者尚未接触过的课程概念。
    NEW = "new"


class PlanStatus(StrEnum):
    """Lifecycle status of a daily learning plan."""

    # 活跃状态：计划当前有效，教学流程可以继续执行其中的项目。
    ACTIVE = "active"

    # 已完成状态：计划中的可执行内容已经用完，需要生成下一份计划。
    EXHAUSTED = "exhausted"

    # 已失效状态：目标、掌握度或其他关键状态发生变化，旧计划不能继续使用。
    INVALID = "invalid"


class RetrievalMode(StrEnum):
    """Strategies for querying curriculum co  ncepts and exercises from the content store."""

    # 精确检索：已知 concept_id，直接查找对应概念或练习。
    EXACT = "exact"

    # 结构化检索：根据 HSK 等级、内容类型等明确字段进行过滤查询。
    STRUCTURED = "structured"

    # 语义检索：根据自然语言描述寻找语义上相关的内容，通常需要向量检索能力。
    SEMANTIC = "semantic"
