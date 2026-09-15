"""
tests/integration/test_pydantic_ai_pipeline.py
Integration tests for curriculum retrieval and structured grading.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_ai import RunContext

from goalcoach.agents.grading_agent import grade_submission
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

    repo.get_concept.side_effect = (
        lambda q: concept if "hsk1_c01" in q or "hello" in q.lower() else None
    )
    repo.list_cards_for_concept.return_value = [card]
    return repo


@pytest.fixture
def mock_chroma_service():
    service = MagicMock()
    service.query_chunks_async = AsyncMock(
        return_value=[
            {
                "content": "Concept: Negation (不 vs 没)\nPattern: 不 + verb / 没 + 有",
                "metadata": {"concept_id": "hsk1_c10", "hsk_level": 1},
            }
        ]
    )
    return service


@pytest.fixture
def sample_learner_state():
    return LearnerState(
        learner_id=uuid4(),
        goal=LearningGoal(title="HSK1 Mastery", target_hsk_level=1),
    )


@pytest.mark.asyncio
async def test_search_hsk_curriculum_exact_match(
    mock_content_repo, mock_chroma_service, sample_learner_state
):
    """Ensure exact concept queries route to SQLite ContentRepository."""
    deps = AgentDeps(
        learner_state=sample_learner_state,
        content_repo=mock_content_repo,
        chroma_service=mock_chroma_service,
    )
    ctx = RunContext(deps=deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    res = await search_hsk_curriculum(ctx, query="hsk1_c01")
    assert "[Curriculum Card - Exact Match: Greetings]" in res
    assert "nǐ hǎo" in res
    mock_chroma_service.query_chunks_async.assert_not_called()


@pytest.mark.asyncio
async def test_search_hsk_curriculum_semantic_fallback(
    mock_content_repo, mock_chroma_service, sample_learner_state
):
    """Ensure non-exact queries fall back to ChromaDB vector search."""
    deps = AgentDeps(
        learner_state=sample_learner_state,
        content_repo=mock_content_repo,
        chroma_service=mock_chroma_service,
    )
    ctx = RunContext(deps=deps, model=MagicMock(), usage=MagicMock(), prompt="test")

    res = await search_hsk_curriculum(ctx, query="how do I say not have")
    assert "[Curriculum Context: hsk1_c10]" in res
    mock_chroma_service.query_chunks_async.assert_called_once()


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
