"""
tests/integration/test_pydantic_ai_pipeline.py
Integration tests for PydanticAI RAG pipeline, tutoring endpoint, and Gemma 4 failover.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic_ai import RunContext
from pydantic_ai.models.test import TestModel

from apps.api.main import app
from goalcoach.agents.grading_agent import grade_submission
from goalcoach.agents.teaching_agent import TutorResponse, chat_with_tutor, tutor_agent
from goalcoach.agents.tools.retrieval_tools import AgentDeps, search_hsk_curriculum
from goalcoach.domain.models import AnswerSubmission, Exercise, LearnerState, LearningGoal


@pytest.fixture
def mock_content_repo():
    repo = MagicMock()
    concept = MagicMock()
    concept.concept_id = "hsk1_c01"
    concept.name_en = "Greetings"
    concept.description_en = "Basic greetings in Mandarin."

    card = MagicMock()
    card.content = "Prompt: 你好\nPinyin: nǐ hǎo\nMeaning: Hello"

    repo.get_concept.side_effect = lambda q: (
        concept if "hsk1_c01" in q or "hello" in q.lower() else None
    )
    repo.list_cards_for_concept.return_value = [card]
    return repo


@pytest.fixture
def sample_learner_state():
    return LearnerState(
        learner_id=uuid4(),
        goal=LearningGoal(title="HSK1 Mastery", target_hsk_level=1),
    )


@pytest.mark.asyncio
async def test_tutor_agent_tool_execution(mock_content_repo, sample_learner_state):
    """Verify tutor agent execution and response schema validation with TestModel."""
    deps = AgentDeps(
        learner_state=sample_learner_state,
        content_repo=mock_content_repo,
    )

    test_model = TestModel(
        custom_result_text='{"reply": "你好 means hello!", "grammar_points": ["hsk1_greeting"], "suggested_practice": "Say 你好 to a friend."}'
    )

    result = await tutor_agent.run("How do I say hello?", deps=deps, model=test_model)
    data = getattr(result, "data", getattr(result, "output", None))
    assert isinstance(data, TutorResponse)
    assert "你好" in data.reply
    assert "hsk1_greeting" in data.grammar_points
    assert data.suggested_practice == "Say 你好 to a friend."


@pytest.mark.asyncio
async def test_search_hsk_curriculum_exact_match(mock_content_repo, sample_learner_state):
    """Ensure exact concept queries route to SQLite ContentRepository."""
    deps = AgentDeps(
        learner_state=sample_learner_state,
        content_repo=mock_content_repo,
    )
    ctx = RunContext(deps=deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    res = await search_hsk_curriculum(ctx, query="hsk1_c01")
    assert "[Curriculum Card - Exact Match: Greetings]" in res
    assert "nǐ hǎo" in res


@pytest.mark.asyncio
async def test_search_hsk_curriculum_unknown_concept(mock_content_repo, sample_learner_state):
    """Ensure unmatched concept queries safely return graceful empty notice."""
    deps = AgentDeps(
        learner_state=sample_learner_state,
        content_repo=mock_content_repo,
    )
    ctx = RunContext(deps=deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    res = await search_hsk_curriculum(ctx, query="unknown_concept_query")
    assert res == "No relevant HSK curriculum cards found."


@pytest.mark.asyncio
async def test_openrouter_failover_to_ollama(mock_content_repo, sample_learner_state, monkeypatch):
    """Assert automatic failover to local Ollama Gemma 4 when OpenRouter raises connection errors."""
    monkeypatch.setenv("GOALCOACH_ENABLE_OLLAMA_FALLBACK", "true")
    deps = AgentDeps(
        learner_state=sample_learner_state,
        content_repo=mock_content_repo,
    )

    mock_fallback_model = TestModel(
        custom_result_text='{"reply": "Fallback response from Gemma 4", "grammar_points": ["fallback"], "suggested_practice": null}'
    )

    orig_run = tutor_agent.run
    call_count = 0

    async def mock_run(prompt, deps=None, model=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            raise httpx.ConnectError("Connection refused by OpenRouter", request=req)
        return await orig_run(prompt, deps=deps, model=mock_fallback_model)

    with (
        patch(
            "goalcoach.infrastructure.llm.pydantic_ai_models.get_ollama_fallback_model",
            return_value=mock_fallback_model,
        ),
        patch.object(tutor_agent, "run", side_effect=mock_run),
    ):
        result, provider = await chat_with_tutor(deps, "Hello!")
        assert isinstance(result, TutorResponse)
        assert "Fallback response" in result.reply
        assert provider.startswith("ollama:")


@pytest.mark.asyncio
async def test_grading_agent_deterministic_fast_path():
    """Verify deterministic fast path for exact reference answer matches."""
    ex_id = uuid4()
    exercise = Exercise(
        id=ex_id,
        concept_id="hsk1_c01",
        prompt="Translate: Hello",
        target_instruction="Write in Chinese",
        reference_answers=["你好", "你好！"],
    )
    submission = AnswerSubmission(
        learner_id=uuid4(),
        exercise_id=ex_id,
        answer="你好",
    )

    result, provider = await grade_submission(exercise, submission)
    assert result.passed_gates is True
    assert result.confidence == 1.0
    assert result.scores.grammatical_correctness == 1.0
    assert provider == "deterministic:rule_match"


def test_api_tutoring_chat_endpoint(mock_content_repo):
    """Verify HTTP POST /api/v1/tutoring/chat endpoint returns 200 and schema response."""
    with patch("goalcoach.agents.teaching_agent.run_with_fallback") as mock_fallback:
        mock_result = MagicMock()
        mock_result.output = TutorResponse(
            reply="你好！很高兴认识你。",
            grammar_points=["hsk1_c01"],
            suggested_practice="Try saying 你好",
        )
        mock_fallback.return_value = (mock_result, "openrouter:qwen/qwen-2.5-72b-instruct")

        client = TestClient(app)
        learner_id = str(uuid4())
        response = client.post(
            "/api/v1/tutoring/chat",
            json={"learner_id": learner_id, "message": "Hello tutor!"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert "response" in payload
        assert "provider" in payload
        assert payload["response"]["reply"] == "你好！很高兴认识你。"
        assert "hsk1_c01" in payload["response"]["grammar_points"]
        assert payload["provider"].startswith("openrouter:")
