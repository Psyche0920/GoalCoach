import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routes.learning import router as learning_router
from apps.api.routes.learning_loop import router as learning_loop_router
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.llm.pydantic_ai_models import AgentOutputError, LLMUnavailableError
from goalcoach.infrastructure.persistence.database import (
    create_learner_schema,
    create_session_factory,
    get_engine,
)
from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    SqlAlchemyLearnerRepository,
)
from goalcoach.infrastructure.telemetry import bind_request_id, reset_request_id


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
            yield
        finally:
            get_engine(session_factory).dispose()
            get_engine(content_session_factory).dispose()

    application = FastAPI(title="GoalCoach API", version="0.1.0", lifespan=lifespan)

    @application.middleware("http")
    async def correlation_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", supplied) else str(uuid4())
        token = bind_request_id(request_id)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response
        finally:
            reset_request_id(token)

    @application.exception_handler(LLMUnavailableError)
    async def handle_llm_unavailable(
        _request: Request,
        _exc: LLMUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "LLM unavailable. Check the configured model provider and try again."},
        )

    @application.exception_handler(AgentOutputError)
    async def handle_agent_output_error(
        _request: Request,
        exc: AgentOutputError,
    ) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

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

    # Health check
    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
