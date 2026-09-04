from collections.abc import AsyncIterator, Collection, Mapping
from contextlib import asynccontextmanager
from typing import Annotated, cast
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
    resolved_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        session_factory = create_session_factory(resolved_settings.database_url)
        content_session_factory = create_session_factory(resolved_settings.content_database_url)
        try:
            create_learner_schema(session_factory)
            application.state.learner_repository = SqlAlchemyLearnerRepository(session_factory)
            prerequisites = ContentRepository(content_session_factory).get_prerequisites()
            application.state.goal_planner = create_goal_planner(
                resolved_settings,
                prerequisites,
            )
            yield
        finally:
            get_engine(session_factory).dispose()
            get_engine(content_session_factory).dispose()

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
    return cast(LearnerRepository, request.app.state.learner_repository)


def get_goal_planner(request: Request) -> GoalPlanner:
    """Resolve the prerequisite-aware planner configured at startup."""
    return cast(GoalPlanner, request.app.state.goal_planner)


async def health() -> dict[str, str]:
    return {"status": "ok"}


async def get_learner(
    learner_id: UUID,
    repository: Annotated[LearnerRepository, Depends(get_learner_repository)],
) -> LearnerState:
    try:
        state = await repository.get(learner_id)
    except LearnerRepositoryError as exc:
        raise HTTPException(status_code=503, detail="Learner storage is unavailable") from exc
    if state is None:
        raise HTTPException(status_code=404, detail="Learner not found")
    return state


async def generate_plan(
    learner_id: UUID,
    repository: Annotated[LearnerRepository, Depends(get_learner_repository)],
    planner: Annotated[GoalPlanner, Depends(get_goal_planner)],
) -> DailyPlan:
    orchestrator = PlanningOrchestrator(planner, repository)
    try:
        return await orchestrator.generate_daily_plan(learner_id)
    except LearnerNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Learner not found") from exc
    except LearnerRepositoryError as exc:
        raise HTTPException(status_code=503, detail="Learner storage is unavailable") from exc


async def submit_answer(submission: AnswerSubmission) -> GradingResult:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"TODO(interface): connect learning loop for {submission.exercise_id}",
    )


app = create_app()
