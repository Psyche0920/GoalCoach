from collections.abc import AsyncIterator, Collection, Mapping
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes.learning import router as learning_router
from apps.api.routes.learning_loop import router as learning_loop_router
from apps.api.routes.tutoring import router as tutoring_router
from goalcoach.agents.goal_planning import DeterministicGoalPlanner
from goalcoach.agents.interfaces import GoalPlanner, LearnerRepository
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.persistence.database import (
    create_learner_schema,
    create_session_factory,
    get_engine,
)
from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    SqlAlchemyLearnerRepository,
)


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
            content_repo = ContentRepository(content_session_factory)
            application.state.content_repository = content_repo
            prerequisites = content_repo.get_prerequisites()
            application.state.goal_planner = create_goal_planner(
                resolved_settings,
                prerequisites,
            )
            yield
        finally:
            get_engine(session_factory).dispose()
            get_engine(content_session_factory).dispose()

    application = FastAPI(title="GoalCoach API", version="0.1.0", lifespan=lifespan)

    # Middleware: Enable CORS for React frontend
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    application.include_router(learning_router)
    application.include_router(learning_loop_router)
    application.include_router(tutoring_router, prefix="/api/v1")

    # Health check
    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


def get_learner_repository(request: Request) -> LearnerRepository:
    """Resolve the request-scoped learner persistence boundary."""
    return cast(LearnerRepository, request.app.state.learner_repository)


def get_goal_planner(request: Request) -> GoalPlanner:
    """Resolve the prerequisite-aware planner configured at startup."""
    return cast(GoalPlanner, request.app.state.goal_planner)


app = create_app()
