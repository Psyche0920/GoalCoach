from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import exists, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from goalcoach.domain.models import LearnerState
from goalcoach.infrastructure.persistence.models import (
    ConceptPrerequisite,
    ContentExercise,
    CurriculumConcept,
    LearnerStateRecord,
    TeachingCard,
)

logger = logging.getLogger(__name__)
# logging.getLogger(__name__)：取得当前模块专用日志器；__name__ 是模块路径。
# 它不会立即输出日志，只在后面的 logger.exception(...) 被调用时记录信息。


class LearnerRepositoryError(RuntimeError):
    """Raised when a learner aggregate cannot be loaded or persisted."""

    # 统一封装数据库与数据校验异常，避免 SQLAlchemy 异常泄漏到业务/API 层。
    # aggregate（聚合）= 一位学习者的完整 LearnerState，而不是其中某一个字段。


class ContentRepository:
    """Queries Database #1 through SQLAlchemy instead of ``sqlite3``."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        # 保存“会话工厂”而非长期 Session；每次操作都获得独立、可关闭的会话。
        # sessionmaker[Session] 表示“能够创建 SQLAlchemy Session 的工厂”。
        # 参数 session_factory 由外部注入，因此仓储不负责决定数据库地址。
        # 为什么使用 Session 工厂：
        # - 每次方法调用创建自己的短生命周期 Session，用完立即关闭。
        # - 不同请求不会共享同一个 Session，减少并发冲突和脏状态。
        # - 测试可注入临时数据库的工厂，生产可注入正式数据库的工厂。
        # `session_factory: sessionmaker[Session]` 中，左边是参数名，右边是类型标注。
        self._session_factory = session_factory

    def list_concepts(self, hsk_level: int = 1) -> list[CurriculumConcept]:
        # hsk_level：筛选等级；未传入时默认查 HSK 1。返回概念对象列表。
        statement = (
            # select(Model)：创建 SELECT 查询，结果转换成指定 ORM 模型。
            # 领域/Pydantic 模型描述业务数据和校验规则；ORM 模型描述数据库表、列和关系。
            # 这里查询数据库，所以必须选择 ORM 模型 CurriculumConcept；SQLAlchemy 才知道
            # 应查询哪张表、哪些列，并把每一行转换成 CurriculumConcept 对象。
            select(CurriculumConcept)
            # where(...)：只保留等级匹配且仍启用的记录；逗号表示 AND。
            .where(
                CurriculumConcept.hsk_level == hsk_level,
                CurriculumConcept.is_active.is_(True),
            )
            # order_by(...)：按课程顺序升序排列。
            .order_by(CurriculumConcept.sequence_no)
        )
        # with：使用后自动关闭 Session。scalars() 只提取 ORM 对象，不返回 SQL 行包装。
        # 为什么使用 scalars：session.execute(statement) 返回 Row 包装对象；
        # session.scalars(statement) 直接提取 SELECT 的第一个实体，得到 CurriculumConcept。
        # list(...) 再把可迭代查询结果一次性转换成声明的 list 返回值。
        with self._session_factory() as session:
            return list(session.scalars(statement))

    def get_teaching_cards(self, concept_id: str) -> list[TeachingCard]:
        # concept_id：目标知识点编号；返回该知识点的教学卡列表。
        statement = (
            select(TeachingCard)
            # join(TeachingCard.concept)：通过 ORM relationship 连接课程概念表。
            .join(TeachingCard.concept)
            .where(
                TeachingCard.concept_id == concept_id,
                CurriculumConcept.is_active.is_(True),
            )
            .order_by(TeachingCard.card_order)
        )
        with self._session_factory() as session:
            return list(session.scalars(statement))

    def get_exercises(
        self, concept_id: str, *, limit: int = 3, randomize: bool = True
    ) -> list[ContentExercise]:
        # `*` 表示后面的 limit/randomize 必须写参数名，避免位置参数含义不清。
        # limit：最多返回几题；randomize：True 随机抽题，False 按固定顺序。
        # func.random() 调用数据库的随机函数，而不是 Python random。
        # func.random() 在数据库执行 ORDER BY RANDOM()，先随机排序再由 LIMIT 截取。
        # Python random 需要先把候选数据全部读入内存再抽样；数据量大时传输和内存成本更高。
        # 代价：数据库随机排序也可能较慢；当前小型 HSK 数据集可接受。
        order = func.random() if randomize else ContentExercise.exercise_order
        statement = (
            select(ContentExercise)
            .join(ContentExercise.concept)
            .where(
                ContentExercise.concept_id == concept_id,
                CurriculumConcept.is_active.is_(True),
            )
            .order_by(order)
            .limit(limit)
        )
        with self._session_factory() as session:
            return list(session.scalars(statement))

    def get_remedial_exercises(self, error_tag: str, *, limit: int = 5) -> list[ContentExercise]:
        # error_tag：学习者错误标签；limit：最多返回的补救练习数。
        # json_each(...) 将 JSON 数组临时展开成多行；table_valued 定义可查询的 key/value 列。
        error_tags = func.json_each(ContentExercise.error_tags).table_valued("key", "value")
        statement = (
            select(ContentExercise)
            .join(ContentExercise.concept)
            .where(
                # exists(...)：只要 JSON 数组中存在一个 value 等于 error_tag，就匹配该练习。
                exists(select(1).select_from(error_tags).where(error_tags.c.value == error_tag)),
                CurriculumConcept.is_active.is_(True),
            )
            .order_by(func.random())
            .limit(limit)
        )
        with self._session_factory() as session:
            return list(session.scalars(statement))

    def get_prerequisites(self) -> dict[str, frozenset[str]]:
        """Return all prerequisite concept IDs grouped by target concept."""
        statement = select(ConceptPrerequisite).order_by(
            ConceptPrerequisite.concept_id,
            ConceptPrerequisite.prerequisite_id,
        )
        grouped: dict[str, set[str]] = {}
        with self._session_factory() as session:
            for rule in session.scalars(statement):
                grouped.setdefault(rule.concept_id, set()).add(rule.prerequisite_id)
        return {
            concept_id: frozenset(prerequisite_ids)
            for concept_id, prerequisite_ids in grouped.items()
        }


class SqlAlchemyLearnerRepository:
    """Atomically persists complete learner aggregates as validated JSON snapshots."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        # 与 ContentRepository 相同：注入 Session 工厂，不保存长期数据库会话。
        self._session_factory = session_factory

    async def get(self, learner_id: UUID) -> LearnerState | None:
        """Load and validate a learner aggregate without blocking the event loop."""
        # 当前 SQLAlchemy 驱动是同步的，因此放入受控工作线程，避免阻塞事件循环。
        # asyncio.to_thread(函数, 参数...)：在线程中执行 `_get_sync(learner_id)`。
        # await：等待本次线程任务完成；等待期间事件循环可处理其他请求。
        return await asyncio.to_thread(self._get_sync, learner_id)

    async def save(self, state: LearnerState) -> None:
        """Insert or replace one aggregate in a single database transaction."""
        # mode="json" 会把 UUID、datetime、枚举转换为数据库 JSON 可接受的值。
        # model_dump 是 Pydantic 方法；返回新的字典，不会修改 state。
        snapshot = state.model_dump(mode="json")
        # 序列化在主协程中先完成；成功后再把同步事务交给工作线程。
        # to_thread 的三个位置参数依次是：目标函数、state、snapshot。
        await asyncio.to_thread(self._save_sync, state, snapshot)

    def _get_sync(self, learner_id: UUID) -> LearnerState | None:
        # 前导下划线表示内部辅助方法；sync 表示它使用同步 SQLAlchemy API。
        try:
            # 上下文管理器确保查询结束后关闭 Session 和底层数据库资源。
            with self._session_factory() as session:
                # 按主键读取，UUID 必须转为与 ORM 列定义一致的字符串。
                # session.get(模型类, 主键)：按主键读取一行；找不到时返回 None。
                record = session.get(LearnerStateRecord, str(learner_id))
                if record is None:
                    return None
                # 数据库 JSON 不能被直接信任，返回领域层前再次执行 Pydantic 校验。
                # model_validate(原始数据)：把 JSON 字典校验并重建为 LearnerState。
                return LearnerState.model_validate(record.state_json)
        except (SQLAlchemyError, ValidationError) as exc:
            # 记录底层异常堆栈和 learner_id，便于运维定位损坏数据或数据库故障。
            # logger.exception(message, extra=...)：记录消息、异常堆栈和结构化 learner_id。
            logger.exception("Failed to load learner state", extra={"learner_id": str(learner_id)})
            # 使用 raise ... from exc 保留完整异常因果链。
            # 外层只依赖 LearnerRepositoryError，仍可通过 __cause__ 查看原始 exc。
            raise LearnerRepositoryError(f"Failed to load learner {learner_id}") from exc

    def _save_sync(self, state: LearnerState, snapshot: dict[str, object]) -> None:
        # state 提供 learner_id/updated_at；snapshot 是准备写入 JSON 列的已序列化字典。
        try:
            # begin() 在正常退出时 commit，异常退出时 rollback，形成原子事务边界。
            # session_factory.begin() 同时创建 Session 和事务：正常退出提交，异常退出回滚并关闭。
            with self._session_factory.begin() as session:
                # 先按主键判断是首次插入，还是替换已有聚合快照。
                record = session.get(LearnerStateRecord, str(state.learner_id))
                if record is None:
                    # 首次保存时创建 ORM 记录；session.add 只登记，退出事务时统一提交。
                    # session.add(record)：登记新增对象；真正 INSERT 通常在 flush/commit 时执行。
                    session.add(
                        # 构造 ORM 行：三个关键字参数分别对应 learner_states 的三列。
                        LearnerStateRecord(
                            learner_id=str(state.learner_id),
                            state_json=snapshot,
                            updated_at=state.updated_at,
                        )
                    )
                else:
                    # 已有记录只替换快照及时间；两次赋值属于同一个数据库事务。
                    record.state_json = snapshot
                    record.updated_at = state.updated_at
        except SQLAlchemyError as exc:
            # 到达这里时 begin() 已回滚，因此不会留下部分写入的状态。
            logger.exception(
                "Failed to save learner state", extra={"learner_id": str(state.learner_id)}
            )
            raise LearnerRepositoryError(f"Failed to save learner {state.learner_id}") from exc


# =============================================================================
# Repository 技术速查
# =============================================================================
#
# 1. Repository（仓储）做什么？
# - 隔离业务层与数据库细节；调用者只使用 get/save 或内容查询方法。
#
# 2. `sessionmaker` 与 `Session` 有什么区别？
# - sessionmaker 是创建 Session 的工厂；Session 是一次数据库工作单元。
# - 不长期共享 Session，可减少连接泄漏和状态污染。
#
# 3. `select → where → join → order_by → limit` 是什么？
# - select 选择模型；where 过滤；join 连接表；order_by 排序；limit 限制数量。
# - 这些调用先构造 SQL statement，执行发生在 session.scalars(statement)。
#
# 4. 为什么同时有 async 方法和 `_get_sync`/`_save_sync`？
# - 对外接口使用 async，适配 FastAPI；底层当前使用同步 SQLAlchemy 驱动。
# - asyncio.to_thread 把同步数据库操作放到线程，避免卡住事件循环。
#
# 5. `try/except` 捕获什么？
# - SQLAlchemyError：连接、查询或提交等数据库错误。
# - ValidationError：数据库 JSON 无法还原成合法 LearnerState。
# - 两者都转换成稳定的 LearnerRepositoryError。
#
# 6. 保存为什么是原子的？
# - session_factory.begin() 管理一个事务；成功全部 COMMIT，失败全部 ROLLBACK。
# - 当前只保证单次 save 原子，不保证“读取→规划→保存”整个过程不存在并发覆盖。
#
# =============================================================================
# 本文件新学到的编码概念
# =============================================================================
#
# 1. Repository Pattern（仓储模式）
# - 业务层不直接写 SQL，而是调用清晰的仓储方法。
# - ContentRepository 负责课程内容查询。
# - SqlAlchemyLearnerRepository 负责学习者状态读写。
#
# 2. Dependency Injection（依赖注入）
# - 构造函数接收 session_factory，不在仓储内部创建全局数据库连接。
# - 同一仓储代码可连接正式数据库、测试数据库或其他兼容数据库。
#
# 3. Unit of Work（工作单元）和短生命周期 Session
# - 一个方法使用一个 Session；Session 追踪这次操作加载和修改的 ORM 对象。
# - `with` 保证资源被关闭；`begin()` 额外保证事务提交或回滚。
#
# 4. SQLAlchemy Statement Builder
# - `select().join().where().order_by().limit()` 只是构造查询，不会立即访问数据库。
# - `session.scalars(statement)` 才执行 SQL，并直接返回 ORM 实体序列。
#
# 5. 数据库端运算
# - `func.random()` 和 `json_each()` 让排序与 JSON 筛选在数据库内完成。
# - 优点是减少传给 Python 的无关数据；缺点是复杂查询依赖具体数据库能力。
#
# 6. Async Adapter（异步适配）
# - 对外 get/save 是 async，符合 FastAPI 和 LearnerRepository Protocol。
# - 底层 SQLite API 是同步的，所以用 asyncio.to_thread 包装阻塞操作。
# - 这是适配方案，不等于底层数据库驱动已经变成真正异步。
#
# 7. Boundary Validation（边界校验）
# - 写入前用 model_dump(mode="json") 将领域模型转换成 JSON 数据。
# - 读取后用 model_validate(...) 重新建立并校验 LearnerState。
# - 数据库返回的字典不能未经校验直接进入业务层。
#
# 8. Exception Translation（异常翻译）
# - 捕获基础设施异常 SQLAlchemyError 和边界校验异常 ValidationError。
# - 对外统一抛出 LearnerRepositoryError，避免上层依赖具体数据库/Pydantic 异常。
# - `raise ... from exc` 保留原始原因，方便日志和调试。
#
# 9. Upsert-like Save（类似 Upsert 的保存）
# - 先按 learner_id 查询；不存在则 INSERT，存在则 UPDATE。
# - 这不是单条数据库原生 UPSERT，而是事务中的“先查再决定”。
#
# =============================================================================
# 本文件的设计决策与权衡
# =============================================================================
#
# 1. 为什么分成两个 Repository？
# - 课程内容主要读取，学习者状态需要持续写入；职责和数据库配置不同。
# - 分开可避免一个类同时承担课程查询和用户状态事务。
#
# 2. 为什么注入 session_factory，而不是注入长期 Session？
# - 每次操作获得独立 Session，生命周期明确，适合并发请求。
# - 代价是每次调用都要创建 Session，但连接池仍可复用底层连接。
#
# 3. 为什么学习者状态保存成完整 JSON 快照？
# - LearnerState 包含多个嵌套 Pydantic 模型，快照方案简单且能一次保存完整状态。
# - 代价是难以只查询 JSON 内的单个字段，并且每次更新会重写整个快照。
#
# 4. 为什么读取后还要 model_validate？
# - 数据库可能包含旧结构、损坏值或人工修改的数据。
# - 重新校验确保仓储返回的一定是符合当前领域规则的 LearnerState。
#
# 5. 为什么使用 asyncio.to_thread？
# - 当前依赖是同步 SQLAlchemy/SQLite；直接调用会阻塞 FastAPI 事件循环。
# - to_thread 改动小，适合当前规模；高并发时应考虑 AsyncSession 和异步驱动。
#
# 6. 为什么捕获两种明确异常，而不是 `except Exception`？
# - 只处理仓储真正能够解释的数据库错误和数据校验错误。
# - 编程错误仍会直接暴露，避免被误报成数据库故障。
#
# 7. 当前事务保证到什么范围？
# - 单次 `_save_sync` 中的 INSERT/UPDATE 是原子的。
# - get 和 save 之间仍可能发生并发覆盖；未来需要 version 字段和乐观锁。
#
# 8. 为什么内容查询返回 ORM 模型？
# - 当前仓储接口直接使用已有 SQLAlchemy 类型，代码简单。
# - 代价是调用层会感知 ORM；系统扩大后可映射成独立领域 DTO，强化边界隔离。
#
# 9. 为什么随机选择交给数据库？
# - LIMIT 前在数据库筛选，避免把全部练习加载到 Python。
# - 当前数据量较小；数据量增大后，ORDER BY RANDOM() 可能需要更高效的抽样策略。
#
# =============================================================================
# 一页总结：Factory、Session、同步方法与线程怎样连接
# =============================================================================
#
# 完整调用链：
#
# `database.py 创建 session_factory`
# → `API 把 factory 注入 Repository`
# → `Repository 的 async get/save 被调用`
# → `asyncio.to_thread` 启动工作线程执行 `_get_sync/_save_sync`
# → `factory 创建一个短生命周期 Session`
# → `Session 执行 SELECT/INSERT/UPDATE`
# → `Session 关闭，结果返回 async 方法`
# → `API/Orchestrator 得到 LearnerState 或保存完成`
#
# 1. Factory（工厂）
# - 工厂不是数据库连接，也不是查询结果；它是“创建 Session 的对象”。
# - 同一个 factory 可以反复创建多个彼此独立的 Session。
# - 它保存数据库 Engine 配置，因此 Repository 不需要知道数据库 URL。
#
# 2. Session（会话）
# - Session 代表一次数据库工作单元，负责执行 SQL、追踪 ORM 对象和管理事务。
# - 查询方法使用 `with factory() as session`：结束时关闭 Session。
# - 保存方法使用 `with factory.begin() as session`：额外自动 COMMIT 或 ROLLBACK。
# - Session 不是登录用户的学习 session；它是 SQLAlchemy 数据库会话。
#
# 3. `_get_sync` / `_save_sync`
# - `_`：Repository 内部使用，不是提供给 API 的公开接口。
# - `get/save`：读取或保存学习者状态。
# - `sync`：内部使用同步 SQLAlchemy，会等待数据库操作完成才返回。
# - `_get_sync` 执行“查 ORM 行 → 取 JSON → 校验为 LearnerState”。
# - `_save_sync` 执行“查 ORM 行 → 不存在则新增 → 存在则替换 → 提交事务”。
#
# 4. Thread（工作线程）
# - 同步数据库操作如果直接运行，会卡住 FastAPI 的事件循环。
# - `asyncio.to_thread(_get_sync, learner_id)` 把同步工作交给另一个线程。
# - 当前请求 await 等结果时，事件循环仍能处理其他用户请求。
# - 线程没有让单条查询更快；它的价值是避免一个等待中的查询阻塞整个事件循环。
#
# =============================================================================
# Content Repository 与 Learner Repository
# =============================================================================
#
# 1. ContentRepository（课程内容仓储）
# - 数据：概念、教学卡、练习和错误标签。
# - 数据库：`goalcoach_hsk1_learning.db`，即内容数据库。
# - 行为：当前只有同步读取，不保存学习者进度。
# - 返回：CurriculumConcept、TeachingCard、ContentExercise 等 ORM 对象。
#
# 2. SqlAlchemyLearnerRepository（学习者状态仓储）
# - 数据：一位用户完整的 LearnerState JSON 快照。
# - 数据库：Settings.database_url 指向的学习者状态数据库。
# - 行为：异步 get/save；内部通过线程运行同步 SQLAlchemy。
# - 返回：经过 Pydantic 校验的 LearnerState，而不是 LearnerStateRecord ORM 行。
#
# 3. 为什么不能合成一个 Repository？
# - 两类数据生命周期不同：课程内容主要读取，用户状态频繁变化并需要事务保存。
# - 两类数据可能位于不同数据库；分开后更容易测试、替换和控制权限。
#
# =============================================================================
# repositories.py 与其他文件的职责区别
# =============================================================================
#
# `domain/models.py`
# - 定义业务对象和校验规则，例如 LearnerState、DailyPlan。
# - 不知道 SQLAlchemy 表和数据库连接。
#
# `persistence/models.py`
# - 定义 ORM 表、数据库列、外键和 relationship。
# - 描述“数据在数据库里长什么样”，但不负责执行查询。
#
# `persistence/database.py`
# - 根据数据库 URL 创建 Engine 和 session_factory，并初始化表。
# - 描述“怎样连接数据库”，但不知道具体业务查询。
#
# `persistence/repositories.py`（本文件）
# - 使用 ORM 模型和 Session 真正执行读取、筛选与保存。
# - 负责在数据库记录与领域对象之间转换，并翻译基础设施异常。
#
# `agents/interfaces.py`
# - 用 Protocol 定义 LearnerRepository 等抽象契约。
# - 只说明调用者可以做什么，不包含 SQLAlchemy 实现。
#
# `ui/orchestrator.py`
# - 安排业务步骤：读取状态 → 生成计划 → 创建新状态 → 保存。
# - 依赖 Repository 接口，但不写 SQL，也不管理 Session。
#
# `apps/api/main.py`
# - 接收 HTTP 请求、注入具体 Repository，并把内部异常转换成 HTTP 状态码。
# - 它是系统入口和组件装配位置，不负责数据库查询细节。
