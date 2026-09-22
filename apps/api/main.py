"""apps/api/main.py
FastAPI entrypoint with lifecycle dependency injection for GoalCoach.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes.learning_loop import handle_tts
from apps.api.routes.learning_loop import router as learning_loop_router
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
            application.state.content_repository = ContentRepository(content_session_factory)
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

    # Consolidated Closed-Loop Router
    application.include_router(learning_loop_router)

    # Health check
    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Direct /api/tts endpoint for frontend audio utilities
    @application.get("/api/tts")
    async def tts_endpoint(text: str = Query(..., min_length=1)) -> Response:
        return await handle_tts(text)

    return application


def get_learner_repository(request: Request) -> SqlAlchemyLearnerRepository:
    """Resolve the request-scoped learner persistence boundary."""
    return cast(SqlAlchemyLearnerRepository, request.app.state.learner_repository)


app = create_app()
