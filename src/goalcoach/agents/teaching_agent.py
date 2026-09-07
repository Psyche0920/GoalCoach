"""
src/goalcoach/agents/teaching_agent.py
Adaptive bilingual Chinese tutor agent implemented with PydanticAI.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from goalcoach.agents.tools.retrieval_tools import AgentDeps, search_hsk_curriculum
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    get_openrouter_model,
    run_with_fallback,
)


class TutorResponse(BaseModel):
    """Structured response schema returned by the tutor agent."""

    reply: str = Field(description="Encouraging bilingual Chinese/English explanation with Pinyin")
    grammar_points: list[str] = Field(default_factory=list, description="HSK concepts referenced")
    suggested_practice: str | None = Field(
        default=None, description="Optional brief follow-up question"
    )


tutor_agent = Agent(
    model=get_openrouter_model(),
    deps_type=AgentDeps,
    output_type=TutorResponse,
    system_prompt=(
        "You are GoalCoach, an adaptive AI tutor for HSK1 Chinese. "
        "Keep explanations concise, encouraging, and provide Pinyin alongside Chinese characters. "
        "Use the `search_hsk_curriculum` tool to verify grammar patterns before answering."
    ),
)

tutor_agent.tool(search_hsk_curriculum)


@tutor_agent.system_prompt
def add_learner_context(ctx: RunContext[AgentDeps]) -> str:
    """Injects dynamic context regarding learner goal and recent error codes into agent prompt."""
    state = ctx.deps.learner_state
    recent_errors = [e.code for e in state.error_profile[-3:]] if state.error_profile else []
    error_note = f"Recent learner mistakes: {', '.join(recent_errors)}." if recent_errors else ""
    level = state.goal.target_hsk_level if state.goal else 1
    return f"Learner HSK Goal Level: {level}. {error_note}".strip()


async def chat_with_tutor(deps: AgentDeps, user_message: str) -> tuple[TutorResponse, str]:
    """Dispatches a user query to the teaching agent with dual-model fallback."""
    result, provider = await run_with_fallback(tutor_agent, user_message, deps=deps)
    return result.output, provider
