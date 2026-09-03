from collections.abc import AsyncIterator, Collection, Mapping
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, status

from goalcoach.agents.goal_planning import DeterministicGoalPlanner
from goalcoach.agents.interfaces import GoalPlanner, LearnerRepository
from goalcoach.domain.models import AnswerSubmission, DailyPlan, GradingResult, LearnerState
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.persistence.database import (
    create_learner_schema,
    create_session_factory,
    get_engine,
)
from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    LearnerRepositoryError,
    SqlAlchemyLearnerRepository,
)
from goalcoach.ui.orchestrator import LearnerNotFoundError, PlanningOrchestrator


def create_goal_planner(
    settings: Settings,
    prerequisites: Mapping[str, Collection[str]],
) -> GoalPlanner:
    """Create the deterministic planner from validated application settings."""
    return DeterministicGoalPlanner(
        item_minutes=settings.planning_item_minutes,
        prerequisites=prerequisites,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API with explicitly configured persistence dependencies."""
    # 测试可显式传入 Settings；生产环境未传入时从 GOALCOACH_* 环境变量读取。
    resolved_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        # 应用启动时创建 Engine/Session 工厂，而不是每个 HTTP 请求重复创建。
        session_factory = create_session_factory(resolved_settings.database_url)
        content_session_factory = create_session_factory(resolved_settings.content_database_url)
        try:
            # 确保 learner_states 表存在；该操作可安全重复执行。
            create_learner_schema(session_factory)
            # 仓储保存到 app.state，供 FastAPI 依赖函数按请求获取同一实例。
            application.state.learner_repository = SqlAlchemyLearnerRepository(session_factory)
            prerequisites = ContentRepository(content_session_factory).get_prerequisites()
            application.state.goal_planner = create_goal_planner(
                resolved_settings,
                prerequisites,
            )
            # yield 之前是启动阶段，之后是关闭阶段；服务请求在 yield 期间执行。
            yield
        finally:
            # 正常关闭或启动失败时都释放连接池。
            get_engine(session_factory).dispose()
            get_engine(content_session_factory).dispose()

    # 使用工厂函数便于测试构建隔离的 FastAPI 实例和数据库配置。
    application = FastAPI(title="GoalCoach API", version="0.1.0", lifespan=lifespan)
    application.add_api_route("/health", health, methods=["GET"])
    application.add_api_route(
        "/api/v1/learners/{learner_id}",
        get_learner,
        methods=["GET"],
        response_model=LearnerState,
    )
    application.add_api_route(
        "/api/v1/learners/{learner_id}/plans",
        generate_plan,
        # POST 表示创建新计划；成功时使用 201 Created，而不是普通查询的 200。
        methods=["POST"],
        response_model=DailyPlan,
        status_code=status.HTTP_201_CREATED,
    )
    application.add_api_route(
        "/api/v1/answers",
        submit_answer,
        methods=["POST"],
        response_model=GradingResult,
    )
    return application


def get_learner_repository(request: Request) -> LearnerRepository:
    """Resolve the request-scoped learner persistence boundary."""
    # 返回 Protocol 类型以保持 API 对实现解耦，实际实例由 lifespan 初始化。
    return request.app.state.learner_repository


def get_goal_planner(request: Request) -> GoalPlanner:
    """Resolve the prerequisite-aware planner configured at startup."""
    return request.app.state.goal_planner


async def health() -> dict[str, str]:
    return {"status": "ok"}


async def get_learner(
    learner_id: UUID,
    repository: Annotated[LearnerRepository, Depends(get_learner_repository)],
) -> LearnerState:
    try:
        # API 只调用仓储契约，不直接编写 SQL 或管理事务。
        state = await repository.get(learner_id)
    except LearnerRepositoryError as exc:
        # 存储故障映射为 503，表示服务暂时不可用，而不是用户资源不存在。
        raise HTTPException(status_code=503, detail="Learner storage is unavailable") from exc
    if state is None:
        # 仓储正常工作但没有匹配记录时，返回语义准确的 404。
        raise HTTPException(status_code=404, detail="Learner not found")
    return state


async def generate_plan(
    learner_id: UUID,
    repository: Annotated[LearnerRepository, Depends(get_learner_repository)],
    planner: Annotated[GoalPlanner, Depends(get_goal_planner)],
) -> DailyPlan:
    # 在组合根组装具体规划器与抽象仓储，业务类本身仍依赖接口。
    orchestrator = PlanningOrchestrator(planner, repository)
    try:
        # 编排器负责读取、规划、复制状态和保存，API 只负责协议转换。
        return await orchestrator.generate_daily_plan(learner_id)
    except LearnerNotFoundError as exc:
        # 把领域/应用层的“找不到学习者”转换成 HTTP 404。
        raise HTTPException(status_code=404, detail="Learner not found") from exc
    except LearnerRepositoryError as exc:
        # 数据库读写失败统一隐藏内部细节，并向客户端返回 503。
        raise HTTPException(status_code=503, detail="Learner storage is unavailable") from exc


async def submit_answer(submission: AnswerSubmission) -> GradingResult:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"TODO(interface): connect learning loop for {submission.exercise_id}",
    )


# 模块级 app 是 Uvicorn 的默认入口；例如 uvicorn apps.api.main:app。
app = create_app()
