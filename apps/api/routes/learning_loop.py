"""apps/api/routes/learning_loop.py
FastAPI router providing the unified closed-loop event endpoint and canonical curriculum/learner queries.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from apps.api.dependencies import get_content_repo, get_learner_repo
from goalcoach.agents.grader_component import GraderComponent
from goalcoach.agents.planning_agent import PlanningWorker
from goalcoach.agents.teaching_agent import TeachingWorker, TutorResponse, chat_with_tutor
from goalcoach.agents.tools.retrieval_tools import AgentDeps
from goalcoach.application.orchestrator import (
    DeterministicOrchestrator,
    OrchestratorResponse,
)
from goalcoach.application.progress_service import ProgressService
from goalcoach.domain.enums import EventType, PlanStatus
from goalcoach.domain.models import (
    ConceptMastery,
    DailyPlan,
    LearnerState,
    LearningGoal,
    utc_now,
)
from goalcoach.infrastructure.persistence.content_service import ContentService
from goalcoach.infrastructure.persistence.models import (
    ContentExercise,
    CurriculumConcept,
    TeachingCard,
)
from goalcoach.infrastructure.persistence.repositories import (
    ContentRepository,
    SqliteLearnerRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["learning-loop"])

tts_cache: dict[str, bytes] = {}


# --- Request / Response Schemas ---


class EventRequest(BaseModel):
    """Inbound request payload for the unified event dispatcher."""

    event_type: EventType
    learner_id: UUID | str = Field(default="learner_001")
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Inbound request payload for the interactive tutor chat."""

    learner_id: UUID | str = "learner_001"
    message: str | None = None
    messages: list[dict[str, Any]] | None = None
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    """Structured response from the interactive tutor chat."""

    response: TutorResponse
    reply: str
    provider: str


# --- Serialization Helpers ---


def serialize_concept(c: CurriculumConcept) -> dict[str, Any]:
    meta = c.metadata_json or {}
    return {
        "conceptId": c.concept_id,
        "hskLevel": c.hsk_level,
        "sequenceNo": c.sequence_no,
        "slug": c.slug,
        "titleZh": c.title_zh,
        "titleEn": c.title_en,
        "conceptType": c.concept_type,
        "category": meta.get("category", "Grammar"),
        "module": meta.get("module", "Greetings"),
        "theme": meta.get("theme", "general"),
        "tags": meta.get("tags", []),
        "isCoreGrammar": meta.get("is_core_grammar", False),
        "communicativeGoal": c.communicative_goal,
        "grammarFocus": c.grammar_focus or [],
        "vocabularyFocus": c.vocabulary_focus or [],
        "difficulty": c.difficulty,
        "estimatedMinutes": c.estimated_minutes,
    }


def serialize_card(card: TeachingCard) -> dict[str, Any]:
    return {
        "id": card.card_order,
        "conceptId": card.concept_id,
        "cardOrder": card.card_order,
        "cardType": card.card_type,
        "promptZh": card.prompt_zh,
        "pinyin": card.pinyin,
        "meaningEn": card.meaning_en,
        "explanationEn": card.explanation_en,
        "exampleZh": card.example_zh,
        "examplePinyin": card.example_pinyin,
        "exampleEn": card.example_en,
        "payload": card.payload or {},
    }


def serialize_exercise(ex: ContentExercise) -> dict[str, Any]:
    ans = ex.answer
    if isinstance(ans, dict):
        if "pairs" in ans:
            ans_str = json.dumps(ans)
        else:
            ans_str = ans.get("value") or ans.get("text") or str(ans)
    else:
        ans_str = str(ans or "")

    accepted = []
    if isinstance(ex.accepted_answers, list):
        accepted.extend([str(a) for a in ex.accepted_answers])
    elif ex.accepted_answers:
        accepted.append(str(ex.accepted_answers))
    if ans_str and ans_str not in accepted:
        accepted.append(ans_str)

    return {
        "id": ex.exercise_id,
        "conceptId": ex.concept_id,
        "exerciseOrder": ex.exercise_order,
        "exerciseType": ex.exercise_type,
        "prompt": ex.prompt,
        "promptPinyin": ex.prompt_pinyin,
        "instruction": ex.instruction,
        "answer": ans_str,
        "options": ex.options if ex.options is not None else [],
        "acceptedAnswers": accepted,
        "explanation": ex.explanation or "",
        "targetTokens": ex.target_tokens or [],
        "errorTags": ex.error_tags or [],
        "difficulty": ex.difficulty,
    }


def compute_progress_summary(
    state: LearnerState, all_concepts: list[Any] | None = None
) -> dict[str, Any]:
    """Computes aggregate progress metrics across the learner's state."""
    total_count = len(all_concepts) if all_concepts else 120
    mastered_count = sum(1 for m in state.mastery.values() if m.mastery_score >= 0.8)
    learned_count = sum(1 for m in state.mastery.values() if m.mastery_score >= 0.3)

    if not state.mastery and state.concept_progress:
        mastered_count = sum(1 for cp in state.concept_progress.values() if cp.is_mastered)
        learned_count = sum(
            1 for cp in state.concept_progress.values() if cp.learned_percent >= 50.0
        )

    course_cov = round((learned_count / total_count) * 100, 1) if total_count else 0.0
    learned_prog = round((learned_count / total_count) * 100, 1) if total_count else 0.0
    mastered_prog = round((mastered_count / total_count) * 100, 1) if total_count else 0.0
    goal_comp = round(state.overall_progress() * 100, 1)

    return {
        "stateVersion": state.state_version,
        "courseCoverage": course_cov,
        "learnedProgress": learned_prog,
        "masteredProgress": mastered_prog,
        "goalCompletion": goal_comp,
        "dailyEffectiveMinutes": 0.0,
    }


def compute_next_action(state: LearnerState) -> str:
    """Deterministically resolves the next suggested action."""
    if state.goal is None or state.goal_changed:
        return "plan_goal"
    if state.review_due():
        return "plan_review"
    if state.active_plan is None or state.active_plan.status != PlanStatus.ACTIVE:
        return "regenerate_plan"
    return "teach"


async def get_or_create_learner(
    learner_id: str,
    repo: SqliteLearnerRepository,
) -> LearnerState:
    """Retrieve existing learner state or bootstrap a fresh one."""
    state = await repo.get(learner_id)
    if not state:
        state = LearnerState(
            learner_id=learner_id,
            display_name=f"Learner {learner_id}",
            goal=LearningGoal(
                title="HSK 1 Complete Goal", target_hsk_level=1, daily_available_minutes=20
            ),
        )
        await repo.save(state)
    return state


# --- Closed-Loop Event Dispatcher ---


@router.post("/events", response_model=OrchestratorResponse)
async def dispatch_learning_event(
    req: EventRequest,
    learner_repo: SqliteLearnerRepository = Depends(get_learner_repo),
    content_repo: ContentRepository = Depends(get_content_repo),
) -> OrchestratorResponse:
    """Dispatches inbound learner events through the Deterministic Orchestrator."""
    content_service = ContentService(content_repo)
    progress_service = ProgressService(learner_repo=learner_repo)
    planning_worker = PlanningWorker()
    teaching_worker = TeachingWorker()
    grader_worker = GraderComponent()

    orchestrator = DeterministicOrchestrator(
        learner_repo=learner_repo,
        content_service=content_service,
        progress_service=progress_service,
        planning_worker=planning_worker,
        teaching_worker=teaching_worker,
        grader_worker=grader_worker,
    )

    return await orchestrator.handle_event(
        event_type=req.event_type,
        payload=req.payload,
        learner_id=req.learner_id,
    )


# --- Learner Aggregate & Plan Queries ---


@router.get("/learners/{learner_id}")
async def get_learner_aggregate(
    learner_id: str,
    learner_repo: SqliteLearnerRepository = Depends(get_learner_repo),
    content_repo: ContentRepository = Depends(get_content_repo),
) -> dict[str, Any]:
    """Fetch complete learner state, deterministic route, and progress summary."""
    state = await get_or_create_learner(learner_id, learner_repo)
    target_level = state.goal.target_hsk_level if state.goal else None
    concepts = content_repo.list_concepts(hsk_level=target_level)
    summary = compute_progress_summary(state, concepts)
    next_action = compute_next_action(state)

    return {
        "state": state,
        "nextAction": next_action,
        "overallProgress": state.overall_progress(),
        "progressSummary": summary,
    }


@router.get("/learners/{learner_id}/today-plan")
async def get_today_plan(
    learner_id: str,
    learner_repo: SqliteLearnerRepository = Depends(get_learner_repo),
    content_repo: ContentRepository = Depends(get_content_repo),
) -> Any:
    """Return the active daily curriculum plan for the learner, generating if needed."""
    state = await get_or_create_learner(learner_id, learner_repo)
    if state.active_plan and not all(item.completed for item in state.active_plan.items):
        return state.active_plan

    content_service = ContentService(content_repo)
    planning_worker = PlanningWorker()
    plan_update = await planning_worker.create_plan(state=state, content_service=content_service)

    daily_plan = DailyPlan(
        learner_id=state.learner_id,
        date=utc_now(),
        status=PlanStatus.ACTIVE,
        items=plan_update.ordered_items,
        rationale=plan_update.adaptation_rationale,
        generated_at=utc_now(),
    )
    state.active_plan = daily_plan
    state.updated_at = utc_now()
    await learner_repo.save(state)
    return daily_plan


class CompleteConceptRequest(BaseModel):
    concept_id: str
    score: float = 100.0
    mode: str = "card"


@router.post("/learners/{learner_id}/complete-concept")
async def complete_concept_endpoint(
    learner_id: str,
    req: CompleteConceptRequest,
    learner_repo: SqliteLearnerRepository = Depends(get_learner_repo),
    content_repo: ContentRepository = Depends(get_content_repo),
) -> dict[str, Any]:
    """Mark concept study as complete and update state mastery."""
    state = await get_or_create_learner(learner_id, learner_repo)
    now = utc_now()
    if req.concept_id not in state.today_studied_concept_ids:
        state.today_studied_concept_ids.append(req.concept_id)

    mastery = state.mastery.get(req.concept_id)
    if mastery is None:
        mastery = ConceptMastery(
            concept_id=req.concept_id,
            mastery_score=min(1.0, req.score / 100.0),
            retention_score=1.0,
            interval_days=1.0,
            evidence_count=1,
            last_reviewed_at=now,
        )
    else:
        mastery.mastery_score = max(mastery.mastery_score, min(1.0, req.score / 100.0))
        mastery.evidence_count += 1
        mastery.last_reviewed_at = now
    state.mastery[req.concept_id] = mastery

    if state.active_plan:
        for item in state.active_plan.items:
            if item.concept_id == req.concept_id:
                item.completed = True
                break

    state.updated_at = now
    await learner_repo.save(state)

    target_level = state.goal.target_hsk_level if state.goal else None
    concepts = content_repo.list_concepts(hsk_level=target_level)
    summary = compute_progress_summary(state, concepts)
    return {
        "state": state,
        "overallProgress": state.overall_progress(),
        "progressSummary": summary,
        "nextAction": compute_next_action(state),
    }


# --- Curriculum Content Queries ---


@router.get("/curriculum/concepts")
async def list_curriculum_concepts(
    level: int | None = Query(default=None, ge=1, le=6, description="Optional HSK level filter (1-6)"),
    content_repo: ContentRepository = Depends(get_content_repo),
) -> list[dict[str, Any]]:
    """List all active curriculum concepts, optionally filtered by HSK level."""
    concepts = content_repo.list_concepts(hsk_level=level)
    return [serialize_concept(c) for c in concepts]


@router.get("/curriculum/concepts/{concept_id}")
async def get_curriculum_concept_details(
    concept_id: str,
    content_repo: ContentRepository = Depends(get_content_repo),
) -> dict[str, Any]:
    """Return concept details, teaching cards, and practice exercises."""
    concept = content_repo.get_concept(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    cards = content_repo.get_teaching_cards(concept.concept_id)
    exercises = content_repo.get_exercises(concept.concept_id, limit=5, randomize=False)

    return {
        "concept": serialize_concept(concept),
        "cards": [serialize_card(c) for c in cards],
        "exercises": [serialize_exercise(e) for e in exercises],
    }


# --- Interactive Tutor Chat ---


@router.post("/tutoring/chat", response_model=ChatResponse)
async def tutoring_chat_endpoint(
    req: ChatRequest,
    learner_repo: SqliteLearnerRepository = Depends(get_learner_repo),
    content_repo: ContentRepository = Depends(get_content_repo),
) -> ChatResponse:
    """Chat with the adaptive bilingual Chinese tutor agent."""
    user_message = req.message
    if not user_message and req.messages:
        for m in reversed(req.messages):
            if m.get("role") == "user" and m.get("content"):
                user_message = m["content"]
                break
    if not user_message:
        user_message = "Hello Coach Baobao!"

    state = await get_or_create_learner(str(req.learner_id), learner_repo)
    deps = AgentDeps(
        learner_state=state,
        content_repo=content_repo,
    )
    tutor_reply, provider = await chat_with_tutor(deps, user_message)
    return ChatResponse(
        response=tutor_reply,
        reply=tutor_reply.reply,
        provider=provider,
    )


# --- Text to Speech (TTS) ---


@router.get("/tts")
async def text_to_speech_prefixed(text: str = Query(..., min_length=1)) -> Response:
    """Proxy Google TTS audio with text normalization and memory caching."""
    return await handle_tts(text)


async def handle_tts(text: str) -> Response:
    clean = re.sub(r"[^\w\u4e00-\u9fa5]+", " ", text).strip()
    if not clean:
        raise HTTPException(status_code=400, detail="No speakable text")

    if clean in tts_cache:
        return Response(
            content=tts_cache[clean],
            media_type="audio/mpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=zh-CN&client=tw-ob&q={quote(clean)}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code != 200:
                raise HTTPException(status_code=502, detail="TTS upstream error")
            tts_cache[clean] = res.content
            return Response(
                content=res.content,
                media_type="audio/mpeg",
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"TTS network error: {exc}") from exc
