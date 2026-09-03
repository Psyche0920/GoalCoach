from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """所有 ORM 数据库表的共同基类。"""

    pass


class CurriculumConcept(Base):
    """课程概念表：一行代表一个可学习的知识点。"""

    __tablename__ = "curriculum_concepts"

    # concept_id：稳定的知识点编号；hsk_level：所属 HSK 等级。
    concept_id: Mapped[str] = mapped_column(String, primary_key=True)
    hsk_level: Mapped[int] = mapped_column(Integer)
    # concept_id 是稳定身份，例如 hsk1_c04；即使排序改变，它也不应改变。
    # sequence_no 是展示/学习顺序，例如 4；调整课程顺序时它可以改变。
    # slug 是便于人阅读和 URL 使用的唯一短名称。
    sequence_no: Mapped[int] = mapped_column(Integer, unique=True)
    slug: Mapped[str] = mapped_column(String, unique=True)
    # title_zh/title_en：中英文标题；concept_type：语法、词汇等知识点类别。
    title_zh: Mapped[str] = mapped_column(String)
    title_en: Mapped[str] = mapped_column(String)
    concept_type: Mapped[str] = mapped_column(String)
    # communicative_goal：学完后能完成的交流任务。
    communicative_goal: Mapped[str] = mapped_column(Text)
    # grammar/vocabulary_focus：该概念重点覆盖的语法和词汇列表。
    grammar_focus: Mapped[list[str]] = mapped_column(JSON, default=list)
    vocabulary_focus: Mapped[list[str]] = mapped_column(JSON, default=list)
    # difficulty：难度；estimated_minutes：预计学习分钟数。
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=6)
    # source_ref 是内容标准/来源标签，不是数据库路径。课程数据仍来自
    # goalcoach_hsk1_learning.db；默认标签 HSK3.0-2026 表示内容依据的标准版本。
    # 这里的 3.0 是“HSK 标准第 3.0 版”，不是“HSK 三级”。实际学习等级由 hsk_level 表示；
    # 因此 HSK 1 内容也可以依据 HSK 3.0 标准编写。
    source_ref: Mapped[str] = mapped_column(String, default="HSK3.0-2026")
    # is_active 控制内容是否对外可用；ContentRepository 的四类查询都会过滤掉 False。
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # metadata_json 保存暂时没有固定列的扩展信息，例如标签、来源备注或实验配置。
    # 当前业务代码尚未读取它；它是为以后扩展预留的，不影响当前规划。
    # Python 属性叫 metadata_json，因为 SQLAlchemy 已使用 metadata；数据库列仍叫 metadata。
    # `mapped_column("metadata", JSON, default=dict)` 分解：
    # - `"metadata"`：真实数据库列名。
    # - `JSON`：该列可保存字典、列表、字符串、数字等 JSON 数据。
    # - `default=dict`：没有提供内容时，为每条新记录创建独立的空字典 `{}`。
    # 用途：未来可加入非核心信息而不用立即新增数据库列，例如 `{"topic": "greeting"}`。
    # 当前代码没有读取这些扩展信息，所以它暂时只是预留字段。
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    # relationship 不创建普通数据列；它让 concept.teaching_cards 可直接访问相关教学卡。
    # back_populates="concept" 把关系与 TeachingCard.concept 配成双向关系。
    # cascade="all, delete-orphan" 表示父对象操作可传递给子对象；脱离父对象的子记录会被删除。
    teaching_cards: Mapped[list[TeachingCard]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )
    # concept.exercises 同理，并与 ContentExercise.concept 组成双向关系。
    exercises: Mapped[list[ContentExercise]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )

    # 技术总结：Mapped[...] 声明 Python 属性类型；mapped_column(...) 声明数据库列规则；
    # relationship(...) 声明 ORM 对象之间的导航关系。详细区别见文件末尾速查。


class TeachingCard(Base):
    """教学卡表：按顺序展示一个知识点的讲解、例句和含义。"""

    __tablename__ = "teaching_cards"
    # 同一 concept_id 下不能出现重复的 card_order。
    __table_args__ = (UniqueConstraint("concept_id", "card_order"),)

    # card_id：教学卡唯一编号；数据库自动生成递增整数。
    card_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # concept_id：所属知识点；外键保证该知识点必须存在。删除知识点时级联删除卡片。
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_concepts.concept_id", ondelete="CASCADE")
    )
    # card_order：卡片展示顺序；card_type：讲解、例句等卡片类别。
    card_order: Mapped[int] = mapped_column(Integer)
    card_type: Mapped[str] = mapped_column(String)
    # prompt_zh：中文展示内容；pinyin：对应拼音；meaning_en：英文含义。
    prompt_zh: Mapped[Optional[str]] = mapped_column(Text)
    pinyin: Mapped[Optional[str]] = mapped_column(Text)
    meaning_en: Mapped[Optional[str]] = mapped_column(Text)
    # explanation_en：英文讲解。
    explanation_en: Mapped[Optional[str]] = mapped_column(Text)
    # example_*：例句的中文、拼音和英文版本。Optional 表示允许没有该内容。
    example_zh: Mapped[Optional[str]] = mapped_column(Text)
    example_pinyin: Mapped[Optional[str]] = mapped_column(Text)
    example_en: Mapped[Optional[str]] = mapped_column(Text)
    # payload：不同卡片类型需要的额外结构化数据。
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # concept：从卡片反向访问所属 CurriculumConcept；与 teaching_cards 对应。
    concept: Mapped[CurriculumConcept] = relationship(back_populates="teaching_cards")


class ContentExercise(Base):
    """练习表：保存题目、答案、解释、错误标签和评分信息。"""

    __tablename__ = "exercises"
    # 同一知识点下，每个练习顺序号必须唯一。
    __table_args__ = (UniqueConstraint("concept_id", "exercise_order"),)

    # exercise_id：练习的唯一编号。
    exercise_id: Mapped[str] = mapped_column(String, primary_key=True)
    # concept_id：所属知识点；删除知识点时，数据库级联删除相关练习。
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_concepts.concept_id", ondelete="CASCADE")
    )
    # exercise_order：练习顺序；exercise_type：选择、填空等题型。
    exercise_order: Mapped[int] = mapped_column(Integer)
    exercise_type: Mapped[str] = mapped_column(String)
    # prompt：题目正文；prompt_pinyin：题目拼音，可以为空；instruction：答题要求。
    prompt: Mapped[str] = mapped_column(Text)
    prompt_pinyin: Mapped[Optional[str]] = mapped_column(Text)
    instruction: Mapped[str] = mapped_column(Text)
    # answer：结构化标准答案；options：选择项，没有选项时可以为 None。
    answer: Mapped[dict[str, Any]] = mapped_column(JSON)
    options: Mapped[Optional[list[str]]] = mapped_column(JSON)
    # accepted_answers：其他可接受答案；explanation：答题解释。
    accepted_answers: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    # target_tokens：必须练习的目标词；error_tags：可用于匹配补救练习的错误标签。
    target_tokens: Mapped[list[str]] = mapped_column(JSON, default=list)
    error_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    # difficulty：题目难度；points：答对可获得的基础分值。
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    points: Mapped[int] = mapped_column(Integer, default=10)
    # metadata_json：预留的额外结构化信息；当前主要流程尚未读取。
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    # concept：从练习反向访问所属知识点；与 CurriculumConcept.exercises 对应。
    concept: Mapped[CurriculumConcept] = relationship(back_populates="exercises")


class ConceptPrerequisite(Base):
    """先修关系表：表示学习 concept_id 前应先掌握 prerequisite_id。"""

    __tablename__ = "concept_prerequisites"
    # 禁止把一个概念设置成它自己的先修概念。
    __table_args__ = (CheckConstraint("concept_id <> prerequisite_id"),)

    # concept_id：准备学习的知识点；同时是组合主键的第一部分。
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_concepts.concept_id", ondelete="CASCADE"), primary_key=True
    )
    # prerequisite_id：必须先掌握的知识点；同时是组合主键的第二部分。
    # 两列共同作为“组合主键”，表示唯一性由两个值一起决定。
    # 例如 `(hsk1_c05, hsk1_c02)` 表示：学习 c05 前要先学 c02。
    # 这对值只能保存一次，但 `(hsk1_c05, hsk1_c03)` 是另一条合法关系。
    # 因此同一个概念可以有多个不同的先修概念，却不能重复保存完全相同的关系。
    prerequisite_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_concepts.concept_id", ondelete="CASCADE"), primary_key=True
    )

    # ForeignKey（外键）把这里的 ID 指向 curriculum_concepts.concept_id。
    # 它保证 concept_id 和 prerequisite_id 都必须是课程表中真实存在的知识点。
    # ondelete="CASCADE" 表示删除被引用的知识点时，数据库也删除相关先修关系，
    # 避免留下指向不存在知识点的无效记录。


# 本文件没有普通业务函数；`mapped_column(...)`、`relationship(...)`、
# `ForeignKey(...)` 等是 SQLAlchemy 配置函数。其参数在文件末尾统一解释。


class LearnerStateRecord(Base):
    """Database record storing one learner's complete state as a JSON snapshot."""

    # 简单解释：这个类描述“学习者状态在数据库表中怎样保存”。
    # `LearnerState` 是程序使用的 Pydantic 对象；`LearnerStateRecord` 是数据库使用的 ORM 对象。
    # aggregate（聚合）在这里就是一位学习者的完整状态：目标、掌握度、错误和当前计划。
    # 英文说明的意思：一条数据库记录，用 JSON 快照保存一位学习者的完整状态。
    # 当前表没有 version 字段，也不保存历史版本。

    # 这是应用状态数据库中的表名，与课程内容数据库的表职责分离。
    __tablename__ = "learner_states"

    # UUID 以标准 36 字符字符串保存，作为每个学习者快照的唯一主键。
    learner_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # 答：ORM = Object-Relational Mapping（对象关系映射），负责连接 Python 类和数据库表：
    # - Python 类 `LearnerStateRecord` ↔ 数据库表 `learner_states`
    # - Python 属性 `learner_id`       ↔ 数据库列 `learner_id`
    #
    # 按符号拆解上一行：
    # - `learner_id`：Python 属性名，同时默认成为数据库列名。
    # - `:`：后面开始写类型标注。
    # - `Mapped[str]`：告诉 SQLAlchemy，这是 ORM 管理的字段，Python 中读取时是字符串。
    # - `=`：把右边创建的数据库列定义绑定到左边属性。
    # - `mapped_column(...)`：创建并配置一列数据库字段。
    # - `String(36)`：数据库用最长 36 字符的字符串保存 UUID。
    # - `primary_key=True`：该列是主键，即每一行的唯一身份证；不能重复或为空。
    #
    # `Mapped` 主要描述 Python 属性类型；`mapped_column` 主要描述数据库列规则。

    # 完整 Pydantic 聚合序列化为 JSON，保证计划与状态一起原子替换。
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # 答：序列化 = 把 Python/Pydantic 对象转换成数据库能够保存的数据。
    # 例如 `LearnerState(active_plan=...)` 会被转换成包含字符串、数字、列表等内容的 JSON。
    #
    # 按符号拆解上一行：
    # - `state_json`：属性名和数据库列名；保存完整学习者状态。
    # - `Mapped[...]`：表示这是一个 SQLAlchemy ORM 字段。
    # - `dict[str, Any]`：Python 读取后得到字典；键是字符串，值可以是多种 JSON 类型。
    # - `mapped_column(JSON, ...)`：数据库列采用 JSON 类型。
    # - `nullable=False`：不允许保存 NULL；每条记录必须包含状态 JSON。
    #
    # “原子替换” = 一次事务成功时整份 JSON 都更新；失败时整次更新回滚。
    # 它不表示保存历史：旧 JSON 会被新 JSON 覆盖。

    # 独立列保留更新时间，便于以后排序、监控或实现乐观并发控制。
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # 答：这一列记录“该状态最后一次保存是什么时间”。按符号拆解：
    # - `updated_at`：Python 属性名和数据库列名。
    # - `Mapped[datetime]`：Python 中的值必须是 datetime 日期时间对象。
    # - `DateTime(timezone=True)`：数据库保存日期时间，并声明它包含时区信息。
    # - `nullable=False`：每条记录都必须有更新时间，不能为 NULL。


# =============================================================================
# LearnerStateRecord 主要问题速查
# =============================================================================
#
# 1. persistence 是什么？
# - 把数据保存到数据库，让程序重启后仍然存在。
#
# 2. ORM 是什么？
# - 用 Python 类和属性表示数据库表和列，减少手写 SQL。
#
# 3. `Mapped` 和 `mapped_column` 有什么区别？
# - `Mapped[str]`：说明 Python 读取该属性时是什么类型。
# - `mapped_column(...)`：说明数据库怎样保存该列，以及主键、可空等规则。
#
# 4. aggregate 是什么？
# - 这里指完整的 LearnerState，而不是其中单独一个计划或掌握度字段。
#
# 5. 当前会保留旧版本吗？
# - 不会。当前每位学习者只有一行，保存新状态会覆盖旧 JSON。
#
# 6. 三个字段分别做什么？
# - `learner_id`：确定这是谁的数据。
# - `state_json`：保存这个人的完整状态。
# - `updated_at`：记录这份状态最后何时更新。
#
# =============================================================================
# SQLAlchemy 技术速查
# =============================================================================
#
# 1. `Mapped[T]` 是什么？
# - 表示“这个 Python 属性由 SQLAlchemy 管理，读取时类型是 T”。
# - 例如 `Mapped[int]` 是整数；`Mapped[list[TeachingCard]]` 是教学卡列表。
#
# 2. `mapped_column(...)` 是什么？
# - 把 Python 属性映射成真实数据库列。
# - 第一个参数常是列类型：String、Integer、Text、Boolean、JSON 或 DateTime。
#
# 3. 常见参数是什么意思？
# - `primary_key=True`：唯一识别一行；两个字段都设置时组成“组合主键”。
# - `unique=True`：该列不允许两行使用相同值。
# - `nullable=False`：该列不能保存 NULL。
# - `default=...`：调用方没有提供值时使用默认值。
# - `autoincrement=True`：插入新行时由数据库自动产生递增整数。
#
# 4. `ForeignKey("表.列", ondelete="CASCADE")` 是什么？
# - 外键要求当前值必须指向另一张表中已经存在的记录。
# - CASCADE 表示删除父记录时，数据库自动删除引用它的子记录。
#
# 5. `relationship(...)` 与 `mapped_column(...)` 有什么区别？
# - `mapped_column` 定义真实列，例如 concept_id。
# - `relationship` 提供 Python 对象导航，例如 card.concept，本身通常不新增列。
# - `back_populates` 指定关系另一端的属性名，让父子对象可以双向访问。
# - `cascade="all, delete-orphan"` 让父对象操作传递给子对象，并删除失去父对象的子记录。
#
# 6. 表级约束是什么？
# - `UniqueConstraint(a, b)`：a 和 b 的组合不能重复。
# - `CheckConstraint(...)`：每行数据必须满足指定条件。
#
# 7. `Optional[str]` 和 `default=list/dict` 是什么？
# - `Optional[str]` 表示 Python 值可以是字符串或 None。
# - `default=list`/`default=dict` 为每条新记录创建独立空容器，避免记录之间共享数据。
