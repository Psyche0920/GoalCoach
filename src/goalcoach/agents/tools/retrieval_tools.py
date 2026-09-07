"""
src/goalcoach/agents/tools/retrieval_tools.py
Agent dependencies and dual-route RAG tools for PydanticAI agents.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import RunContext

from goalcoach.domain.models import LearnerState
from goalcoach.infrastructure.persistence.repositories import ContentRepository
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService


@dataclass
class AgentDeps:
    """Dependency container injected into PydanticAI tutor agent runs."""

    learner_state: LearnerState
    content_repo: ContentRepository
    chroma_service: ChromaService


async def search_hsk_curriculum(ctx: RunContext[AgentDeps], query: str, top_k: int = 2) -> str:
    """Searches curriculum cards via exact concept match first, falling back to ChromaDB vector search."""
    # Fast path: exact concept match in SQLite Database #1
    concept = ctx.deps.content_repo.get_concept(query.strip())
    if concept:
        cards = ctx.deps.content_repo.list_cards_for_concept(concept.concept_id)
        content = "\n".join([c.content for c in cards]) if cards else (concept.description_en or "")
        return f"[Curriculum Card - Exact Match: {concept.name_en}]\n{content}"

    # Semantic path: ChromaDB similarity search
    level = ctx.deps.learner_state.goal.target_hsk_level if ctx.deps.learner_state.goal else 1
    chunks = await ctx.deps.chroma_service.query_chunks_async(
        query_text=query, top_k=top_k, level=level
    )
    if not chunks:
        return "No relevant HSK curriculum cards found."

    formatted: list[str] = []
    for c in chunks:
        formatted.append(
            f"[Curriculum Context: {c.get('metadata', {}).get('concept_id', 'General')}]\n{c.get('content')}"
        )
    return "\n---\n".join(formatted)
