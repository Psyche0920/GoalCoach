"""
src/goalcoach/agents/tools/retrieval_tools.py
Agent dependencies and curriculum retrieval tools for PydanticAI agents.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import RunContext

from goalcoach.domain.models import LearnerState
from goalcoach.infrastructure.persistence.repositories import ContentRepository


@dataclass
class AgentDeps:
    """Dependency container injected into PydanticAI tutor agent runs."""

    learner_state: LearnerState
    content_repo: ContentRepository


async def search_hsk_curriculum(ctx: RunContext[AgentDeps], query: str) -> str:
    """Searches curriculum cards via deterministic concept match in SQLite Database #1."""
    concept = ctx.deps.content_repo.get_concept(query.strip())
    if concept:
        cards = ctx.deps.content_repo.list_cards_for_concept(concept.concept_id)
        content = "\n".join([c.content for c in cards]) if cards else (concept.description_en or "")
        return f"[Curriculum Card - Exact Match: {concept.name_en}]\n{content}"

    return "No relevant HSK curriculum cards found."
