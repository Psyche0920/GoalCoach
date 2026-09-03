"""Deterministic top-level workflow orchestrator and routing logic for GoalCoach."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from goalcoach.agents.interfaces import GoalPlanner, LearnerRepository
from goalcoach.domain.enums import PlanStatus
from goalcoach.domain.models import DailyPlan, LearnerState, utc_now


class LearnerNotFoundError(LookupError):
    """Raised when an orchestration request targets an unknown learner."""

    # 查询成功但 learner_id 不存在；API 层会将它转换成 HTTP 404。


class PlanningOrchestrator:
    """Coordinates deterministic plan creation and durable aggregate replacement."""

    def __init__(self, planner: GoalPlanner, repository: LearnerRepository) -> None:
        # 注入两个接口：规划器负责生成计划，仓储负责读写状态。
        self._planner = planner
        self._repository = repository

    async def generate_daily_plan(self, learner_id: UUID) -> DailyPlan:
        """Generate and atomically persist a plan without mutating loaded state."""
        # 1. 读取当前学习者状态。
        state = await self._repository.get(learner_id)
        if state is None:
            raise LearnerNotFoundError(f"Learner {learner_id} was not found")

        # 2. 根据当前状态生成计划；规划器不负责保存。
        plan = await self._planner.create_plan(state)

        # 3. 深复制状态，只在副本中替换计划和更新时间。
        updated_state = state.model_copy(
            update={"active_plan": plan, "updated_at": utc_now()},
            deep=True,
        )

        # 4. 原子保存整个新状态；失败时仓储回滚。
        await self._repository.save(updated_state)

        # 5. 返回计划给 API 调用者。
        return plan


class NextAction(StrEnum):
    """The next deterministic action or workflow branch to execute."""

    PLAN_GOAL = "plan_goal"
    PLAN_REVIEW = "plan_review"
    REGENERATE_PLAN = "regenerate_plan"
    TEACH = "teach"


def route(state: LearnerState) -> NextAction:
    """Deterministically routes the learner's state to the next action based on priority rules.

    Priority Rules:
        1. Goal Planning: If `state.goal is None` or `state.goal_changed` is True, returns `NextAction.PLAN_GOAL`.
        2. Spaced Review: If `state.review_due()` is True, returns `NextAction.PLAN_REVIEW`.
        3. Plan Regeneration: If `state.active_plan is None` or `state.active_plan.status != PlanStatus.ACTIVE`,
           returns `NextAction.REGENERATE_PLAN`.
        4. Interactive Teaching (Default): Otherwise returns `NextAction.TEACH`.

    Args:
        state: The current aggregate state of the learner.

    Returns:
        The selected `NextAction` to be handled by the execution layer.
    """

    # 只选择下一步，不执行下一步。
    if state.goal is None or state.goal_changed:
        return NextAction.PLAN_GOAL
    if state.review_due():
        return NextAction.PLAN_REVIEW
    if state.active_plan is None or state.active_plan.status != PlanStatus.ACTIVE:
        return NextAction.REGENERATE_PLAN
    return NextAction.TEACH


# =============================================================================
# 主要问题速查（中文）
# =============================================================================
#
# 1. 这个文件负责什么？
# - `route()` 选择下一步。
# - `PlanningOrchestrator` 执行“读取 → 规划 → 复制 → 保存”。
#
# 2. `LearnerRepository` 在哪里？
# - 接口：`goalcoach/agents/interfaces.py`。
# - SQLAlchemy 实现：`infrastructure/persistence/repositories.py`。
#
# 3. `None` 和空状态有什么区别？
# - `None`：数据库中没有这个学习者，API 返回 404。
# - 空状态：LearnerState 存在，但 goal 或 active_plan 尚未设置。
#
# 4. 为什么用 `async/await`？
# - 数据库读写需要等待；等待时服务器可以处理其他请求。
# - `await` 只等当前操作完成，不等待未来状态或下一次计划。
# - 同时可处理的工作包括其他用户的 API 请求、数据库查询和网络 I/O。
#
# 5. 什么是异步契约？
# - Protocol 把方法定义为 `async def`，所有实现和调用者都按 `await` 方式使用。
#
# 6. 什么是 persist？
# - 把内存中的状态写进数据库；服务器重启后仍可读取。
# - 它不是等待，也不会自动持续更新状态。
#
# 7. 什么是原子保存？
# - `state_json` 和 `updated_at` 要么全部提交，要么全部回滚。
# - “读取 → 规划 → 保存”整体目前不是一个长事务。
#
# 8. 什么是乐观锁？
# - 保存时检查版本号；若别人已先更新，则拒绝覆盖旧数据。
# - 当前尚未实现，未来多请求并发更新同一学习者时需要它。
#
# 9. 为什么 `deep=True`？
# - 防止新旧状态共享 mastery、sessions 等可变嵌套对象。
# - 它不保存历史；当前数据库只保留最新快照。
#
# 10. 本函数更新哪些用户状态？
# - 只更新 `active_plan` 和 `updated_at`。
# - 不更新 mastery、error_profile 或项目完成状态。
#
# 11. 没有计划时会怎样？
# - 没有 goal：返回 PLAN_GOAL。
# - 有 goal 但 active_plan=None：返回 REGENERATE_PLAN。
# - `or` 会短路，因此 active_plan=None 时不会访问 `.status`。
#
# 12. 什么时候计划不是 ACTIVE？
# - EXHAUSTED：计划项目已完成。
# - INVALID：状态变化使旧计划失效。
# - 设置这两个状态的真实业务流程目前尚未实现。
