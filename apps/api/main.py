from collections.abc import AsyncIterator, Collection, Mapping
from contextlib import asynccontextmanager
from typing import Annotated, cast
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status

from goalcoach.agents.goal_planning import DeterministicGoalPlanner
from goalcoach.agents.interfaces import GoalPlanner, LearnerRepository
from goalcoach.domain.models import (
    AnswerSubmission,
    ChatReply,
    ChatRequest,
    ChatResponse,
    DailyPlan,
    GradingResult,
    LearnerState,
    LearningGoal,
)
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
            application.state.settings = resolved_settings
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
    application.add_api_route(
        "/api/v1/tutoring/chat",
        chat,
        methods=["POST"],
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


async def chat(
    body: ChatRequest,
    http_request: Request,
    repository: Annotated[LearnerRepository, Depends(get_learner_repository)],
) -> ChatResponse:
    settings = cast(Settings, http_request.app.state.settings)
    learner_id = UUID(body.learner_id)

    state = await repository.get(learner_id)
    if state is None:
        state = LearnerState(
            learner_id=learner_id,
            goal=LearningGoal(title="HSK 1 — Mandarin basics", target_hsk_level=1),
        )
        await repository.save(state)

    system_prompt = (
        "You are GoalCoach, a friendly and encouraging HSK (Chinese) learning tutor.\n"
        "The learner is studying Mandarin Chinese. Help them with vocabulary, grammar, "
        "pronunciation tips, and cultural context.\n"
        "Keep replies concise and encouraging. Use pinyin alongside Chinese characters.\n"
        "After explaining, suggest a practice activity.\n"
        "If the learner says 你好 for the first time, greet them warmly and set up their learning goal."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": body.message},
    ]

    provider = "unknown"
    reply_text = ""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.llm_api_key}",
                },
                json={
                    "model": settings.llm_model,
                    "messages": messages,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            reply_text = data["choices"][0]["message"]["content"]
            provider = settings.llm_model or "llm"
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM call failed: {exc}",
        ) from exc

    grammar_points: list[str] = []
    if "了" in reply_text and "le" in reply_text.lower():
        grammar_points.append("了 (le) — aspect marker")
    if "过" in reply_text and "guo" in reply_text.lower():
        grammar_points.append("过 (guo) — experiential aspect")
    if "的" in reply_text and "de" in reply_text.lower():
        grammar_points.append("的 (de) — possessive/attributive")
    if "是" in reply_text and "shi" in reply_text.lower():
        grammar_points.append("是 (shì) — to be")

    await repository.save(state)

    return ChatResponse(
        response=ChatReply(
            reply=reply_text,
            grammar_points=grammar_points,
            suggested_practice="Try writing a sentence with the new vocabulary!",
        ),
        provider=provider,
    )


app = create_app()
