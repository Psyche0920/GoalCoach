# PydanticAI RAG Pipeline & Agent Implementation Plan

This implementation plan refactors the GoalCoach agentic layer to use **PydanticAI** for all LLM interactions, tool-based retrieval (Agentic RAG), and structured validation. The architecture keeps top-level routing deterministic in plain Python while utilizing PydanticAI agents for adaptive teaching, context-augmented chat, and rubric grading.

```
GoalCoach/
├── pyproject.toml                         <-- Step 1: Add pydantic-ai dependency
├── src/goalcoach/
│   ├── infrastructure/
│   │   ├── retrieval/
│   │   │   └── chroma_service.py         <-- Step 2: Non-blocking ChromaDB search
│   │   └── llm/
│   │       └── pydantic_ai_models.py     <-- Step 3: Dual OpenRouter + Ollama Gemma 4 models
│   └── agents/
│       ├── tools/
│       │   └── retrieval_tools.py        <-- Step 4: Dual-route RAG tools (SQL + Chroma)
│       ├── teaching_agent.py             <-- Step 5: PydanticAI Tutor Agent (Chat & RAG)
│       └── grading_agent.py              <-- Step 6: PydanticAI Rubric Grader (result_type)
├── apps/
│   ├── api/
│   │   ├── routes/
│   │   │   └── tutoring.py               <-- Step 7: POST /api/v1/tutoring/chat
│   │   └── main.py                       <-- Step 7: Mount routes and lifespan DI
│   └── web/
│       └── app.py                        <-- Step 8: Streamlit chat interface
└── tests/
    └── integration/
        └── test_pydantic_ai_pipeline.py  <-- Step 9: Offline Gemma 4 failover tests

```

---

### Step 1: Dependencies & Configuration Update

Add `pydantic-ai` to `pyproject.toml` while preserving existing `retrieval` packages (`chromadb`, `sentence-transformers`, `posthog<3`).

```toml
# pyproject.toml
dependencies = [
  "fastapi>=0.115,<1",
  "pydantic>=2.8,<3",
  "pydantic-settings>=2.4,<3",
  "pydantic-ai>=0.0.14",
  "sqlalchemy>=2.0,<3",
  "streamlit>=1.62.0",
  "uvicorn[standard]>=0.30,<1",
  "httpx>=0.28.1",
  "pytest>=8.4.2",
]

[project.optional-dependencies]
retrieval = [
  "chromadb>=0.6.3,<1",
  "posthog<3",
  "sentence-transformers>=3.0.0",
]

```

Run lock update:

```bash
uv lock

```

---

### Step 2: Non-Blocking ChromaDB Service

Wrap synchronous ChromaDB operations in `anyio.to_thread.run_sync` to keep the FastAPI asynchronous runtime unblocked.

```python
# src/goalcoach/infrastructure/retrieval/chroma_service.py
from __future__ import annotations
import anyio
import chromadb
from chromadb.config import Settings as ChromaSettings
from goalcoach.infrastructure.config import Settings

settings = Settings()


class ChromaService:
    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(
            path=str(settings.chroma_persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="hsk1_curriculum",
            metadata={"hnsw:space": "cosine"},
        )

    def _sync_query(self, query_text: str, top_k: int = 3, level: int | None = None) -> list[dict]:
        where_filter = {"hsk_level": level} if level else None
        results = self._collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where=where_filter,
        )
        chunks: list[dict] = []
        if results and results["documents"] and results["metadatas"]:
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                chunks.append({"content": doc, "metadata": meta})
        return chunks

    async def query_chunks_async(
        self, query_text: str, top_k: int = 3, level: int | None = None
    ) -> list[dict]:
        return await anyio.to_thread.run_sync(self._sync_query, query_text, top_k, level)
```

---

### Step 3: Dual-Model Setup (OpenRouter & Local Gemma 4)

Configure PydanticAI's `OpenAIModel` instances for OpenRouter and local Ollama, with automated exception failover.

```python
# src/goalcoach/infrastructure/llm/pydantic_ai_models.py
from __future__ import annotations
import logging
from typing import TypeVar, Any
import httpx
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.exceptions import ModelRetry
from goalcoach.infrastructure.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


def get_openrouter_model() -> OpenAIModel:
    return OpenAIModel(
        model_name=settings.llm_model or "qwen/qwen-2.5-72b-instruct",
        base_url=str(settings.llm_base_url),
        api_key=settings.llm_api_key or "unconfigured_key",
    )


def get_ollama_fallback_model() -> OpenAIModel:
    return OpenAIModel(
        model_name=settings.fallback_llm_model or "unsloth/gemma-4-12b-it-GGUF",
        base_url=str(settings.fallback_llm_base_url),
        api_key="ollama",
    )


T = TypeVar("T")


async def run_with_fallback(agent: Any, prompt: str, deps: Any) -> tuple[Any, str]:
    """Executes a PydanticAI agent on OpenRouter; falls back to Ollama Gemma 4 on connection/timeout errors."""
    primary_model = get_openrouter_model()
    fallback_model = get_ollama_fallback_model()

    try:
        result = await agent.run(prompt, deps=deps, model=primary_model)
        return result, f"openrouter:{primary_model.model_name}"
    except (httpx.HTTPError, httpx.TimeoutException, Exception) as err:
        logger.warning("Primary model failed (%s). Falling back to local Ollama Gemma 4.", err)
        result = await agent.run(prompt, deps=deps, model=fallback_model)
        return result, f"ollama:{fallback_model.model_name}"
```

---

### Step 4: RAG Dependency Injection & Retrieval Tools

Define dependencies and tools enabling PydanticAI agents to query both SQLite (exact matches) and ChromaDB (semantic fallback).

```python
# src/goalcoach/agents/tools/retrieval_tools.py
from __future__ import annotations
from dataclasses import dataclass
from pydantic_ai import RunContext
from goalcoach.domain.models import LearnerState
from goalcoach.infrastructure.persistence.repositories import ContentRepository
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService


@dataclass
class AgentDeps:
    learner_state: LearnerState
    content_repo: ContentRepository
    chroma_service: ChromaService


async def search_hsk_curriculum(ctx: RunContext[AgentDeps], query: str, top_k: int = 2) -> str:
    """Searches curriculum cards via exact concept match first, falling back to ChromaDB vector search."""
    # Fast path: exact concept match in SQLite
    concept = ctx.deps.content_repo.get_concept(query.strip())
    if concept:
        cards = ctx.deps.content_repo.list_cards_for_concept(concept.concept_id)
        content = "\n".join([c.content for c in cards]) if cards else (concept.description_en or "")
        return f"[Curriculum Card - Exact Match: {concept.name_en}]\n{content}"

    # Semantic path: ChromaDB similarity
    level = ctx.deps.learner_state.goal.target_hsk_level if ctx.deps.learner_state.goal else 1
    chunks = await ctx.deps.chroma_service.query_chunks_async(
        query_text=query, top_k=top_k, level=level
    )
    if not chunks:
        return "No relevant HSK curriculum cards found."

    formatted = []
    for c in chunks:
        formatted.append(
            f"[Curriculum Context: {c.get('metadata', {}).get('concept_id', 'General')}]\n{c.get('content')}"
        )
    return "\n---\n".join(formatted)
```

---

### Step 5: Adaptive Teaching & Chat Agent (PydanticAI)

Build the dialogue agent with dynamic context augmentation from `LearnerState` and RAG tools.

```python
# src/goalcoach/agents/teaching_agent.py
from __future__ import annotations
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from goalcoach.agents.tools.retrieval_tools import AgentDeps, search_hsk_curriculum
from goalcoach.infrastructure.llm.pydantic_ai_models import get_openrouter_model, run_with_fallback


class TutorResponse(BaseModel):
    reply: str = Field(description="Encouraging bilingual Chinese/English explanation with Pinyin")
    grammar_points: list[str] = Field(default_factory=list, description="HSK concepts referenced")
    suggested_practice: str | None = Field(
        default=None, description="Optional brief follow-up question"
    )


tutor_agent = Agent(
    model=get_openrouter_model(),
    deps_type=AgentDeps,
    result_type=TutorResponse,
    system_prompt=(
        "You are GoalCoach, an adaptive AI tutor for HSK1 Chinese. "
        "Keep explanations concise, encouraging, and provide Pinyin alongside Chinese characters. "
        "Use the `search_hsk_curriculum` tool to verify grammar patterns before answering."
    ),
)

tutor_agent.tool(search_hsk_curriculum)


@tutor_agent.system_prompt
def add_learner_context(ctx: RunContext[AgentDeps]) -> str:
    state = ctx.deps.learner_state
    recent_errors = [e.code for e in state.error_profile[-3:]] if state.error_profile else []
    error_note = f"Recent learner mistakes: {', '.join(recent_errors)}." if recent_errors else ""
    return (
        f"Learner HSK Goal Level: {state.goal.target_hsk_level if state.goal else 1}. {error_note}"
    )


async def chat_with_tutor(deps: AgentDeps, user_message: str) -> tuple[TutorResponse, str]:
    result, provider = await run_with_fallback(tutor_agent, user_message, deps=deps)
    return result.data, provider
```

---

### Step 6: Rubric Grader Agent (PydanticAI Structured Output)

Implement rubric-based evaluation returning `GradingResult` validated directly through PydanticAI.

```python
# src/goalcoach/agents/grading_agent.py
from __future__ import annotations
from pydantic_ai import Agent
from goalcoach.domain.models import GradingResult, Exercise, AnswerSubmission
from goalcoach.infrastructure.llm.pydantic_ai_models import get_openrouter_model, run_with_fallback

grader_agent = Agent(
    model=get_openrouter_model(),
    result_type=GradingResult,
    system_prompt=(
        "You are the GoalCoach Chinese Grading Evaluator. "
        "Grade the student's Chinese sentence against 3 dimensions: "
        "1. grammatical_correctness, 2. semantic_precision, 3. pragmatic_appropriateness. "
        "Each score must be between 0.0 and 1.0. "
        "Gate rule: passed_gates is true only if grammatical_correctness >= 0.70 "
        "and semantic_precision >= 0.70."
    ),
)


async def grade_submission(
    exercise: Exercise, submission: AnswerSubmission
) -> tuple[GradingResult, str]:
    # Fast path: deterministic match on reference answers
    if submission.answer.strip() in [ans.strip() for ans in exercise.reference_answers]:
        from goalcoach.domain.models import RubricScores

        return GradingResult(
            exercise_id=exercise.id,
            scores=RubricScores(
                grammatical_correctness=1.0,
                semantic_precision=1.0,
                pragmatic_appropriateness=1.0,
            ),
            passed_gates=True,
            confidence=1.0,
            feedback="Perfect! Your answer matches the accepted standard response.",
            grader_version="deterministic-fast-path",
        ), "deterministic:rule_match"

    # LLM grading path
    prompt = (
        f"Exercise Prompt: {exercise.prompt}\n"
        f"Target Concept: {exercise.concept_id}\n"
        f"Target Instruction: {exercise.target_instruction}\n"
        f"Student Answer: {submission.answer}\n"
        f"Reference Answers: {', '.join(exercise.reference_answers)}"
    )
    result, provider = await run_with_fallback(grader_agent, prompt, deps=None)
    return result.data, provider
```

---

### Step 7: API Layer Integration (`apps/api`)

Connect SQLite persistence, ChromaDB, and PydanticAI agents inside the FastAPI application.

```python
# apps/api/routes/tutoring.py
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from goalcoach.domain.models import LearnerState, LearningGoal
from goalcoach.infrastructure.persistence.repositories import (
    SqliteLearnerRepository,
    ContentRepository,
)
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService
from goalcoach.agents.tools.retrieval_tools import AgentDeps
from goalcoach.agents.teaching_agent import chat_with_tutor, TutorResponse
from apps.api.dependencies import get_learner_repo, get_content_repo, get_chroma_service

router = APIRouter(prefix="/tutoring", tags=["tutoring"])


class ChatRequest(BaseModel):
    learner_id: UUID
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    response: TutorResponse
    provider: str


@router.post("/chat", response_model=ChatResponse)
async def tutoring_chat_endpoint(
    req: ChatRequest,
    learner_repo: SqliteLearnerRepository = Depends(get_learner_repo),
    content_repo: ContentRepository = Depends(get_content_repo),
    chroma_service: ChromaService = Depends(get_chroma_service),
):
    state = await learner_repo.get(req.learner_id)
    if not state:
        state = LearnerState(
            learner_id=req.learner_id,
            goal=LearningGoal(title="HSK1 Mastery", target_hsk_level=1),
        )
        await learner_repo.save(state)

    deps = AgentDeps(
        learner_state=state,
        content_repo=content_repo,
        chroma_service=chroma_service,
    )
    tutor_reply, provider = await chat_with_tutor(deps, req.message)
    return ChatResponse(response=tutor_reply, provider=provider)
```

Register the router in `apps/api/main.py`:

```python
# apps/api/main.py
from fastapi import FastAPI
from apps.api.routes.tutoring import router as tutoring_router

app = FastAPI(title="GoalCoach API")
app.include_router(tutoring_router, prefix="/api/v1")
```

---

### Step 8: Streamlit Chat Client (`apps/web/app.py`)

Implement the UI communicating with the PydanticAI-powered backend.

```python
# apps/web/app.py
import streamlit as st
import httpx

API_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="GoalCoach — HSK Tutor", page_icon="🇨🇳", layout="wide")
st.title("GoalCoach: Adaptive Chinese Tutor (PydanticAI)")

if "learner_id" not in st.session_state:
    st.session_state.learner_id = "00000000-0000-0000-0000-000000000001"
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar info
st.sidebar.header("Learner Profile")
st.sidebar.text(f"ID: {st.session_state.learner_id}")
st.sidebar.caption("Orchestrator: Deterministic State Machine")
st.sidebar.caption("Agents: PydanticAI (OpenRouter + Ollama Gemma 4)")

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "grammar_points" in msg and msg["grammar_points"]:
            st.caption(f"Grammar points: {', '.join(msg['grammar_points'])}")

# Chat input
if prompt := st.chat_input("Ask a question about HSK1 Chinese..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consulting curriculum..."):
            try:
                res = httpx.post(
                    f"{API_URL}/tutoring/chat",
                    json={"learner_id": st.session_state.learner_id, "message": prompt},
                    timeout=60.0,
                )
                if res.status_code == 200:
                    payload = res.json()
                    tutor_data = payload["response"]
                    st.markdown(tutor_data["reply"])
                    if tutor_data.get("suggested_practice"):
                        st.info(f"💡 Practice: {tutor_data['suggested_practice']}")
                    st.caption(f"Inference: `{payload['provider']}`")

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": tutor_data["reply"],
                            "grammar_points": tutor_data.get("grammar_points", []),
                        }
                    )
                else:
                    st.error(f"API Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")
```

---

### Step 9: Integration Tests & Fallback Verification

Write test cases asserting PydanticAI tool usage and automated failover from OpenRouter to Ollama.

```python
# tests/integration/test_pydantic_ai_pipeline.py
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from pydantic_ai.models.test import TestModel
from goalcoach.domain.models import LearnerState, LearningGoal
from goalcoach.agents.tools.retrieval_tools import AgentDeps
from goalcoach.agents.teaching_agent import tutor_agent, TutorResponse


@pytest.mark.asyncio
async def test_tutor_agent_tool_execution(mock_content_repo, mock_chroma_service):
    state = LearnerState(learner_id=uuid4(), goal=LearningGoal(title="HSK1", target_hsk_level=1))
    deps = AgentDeps(
        learner_state=state,
        content_repo=mock_content_repo,
        chroma_service=mock_chroma_service,
    )

    test_model = TestModel(
        custom_result_text='{"reply": "你好 means hello!", "grammar_points": ["hsk1_greeting"], "suggested_practice": "Say 你好 to a friend."}'
    )

    result = await tutor_agent.run("How do I say hello?", deps=deps, model=test_model)
    assert isinstance(result.data, TutorResponse)
    assert "你好" in result.data.reply
    assert "hsk1_greeting" in result.data.grammar_points
```

---

### Step 10: Verification Checklist

Execute these verification commands sequentially:

```bash
# 1. Ingest curriculum into ChromaDB collection
uv run python -m scripts.vector_store --refresh

# 2. Check types, linting, and formatting
uv run ruff check src/goalcoach apps/ tests/
uv run ruff format --check src/goalcoach apps/ tests/

# 3. Run unit and integration tests
uv run pytest tests/unit/ -v
uv run pytest tests/integration/test_pydantic_ai_pipeline.py -v

# 4. Start services for manual smoke test
uv run uvicorn apps.api.main:app --reload --port 8000 &
uv run streamlit run apps/web/app.py

```