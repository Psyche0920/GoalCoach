"""
src/goalcoach/agents/teaching_agent.py
Adaptive bilingual Chinese tutor agent implemented with PydanticAI.
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from goalcoach.agents.tools.retrieval_tools import AgentDeps, search_hsk_curriculum
from goalcoach.domain.models import GradingResult
from goalcoach.domain.models import (
    TeachingAction,
    TeachingSession,
)
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    get_openrouter_model,
    run_with_fallback,
)

# ---------------------------------------------------------------------------
# Teaching Agent
# ---------------------------------------------------------------------------

teaching_agent = Agent(
    model=get_openrouter_model(),
    deps_type=AgentDeps,
    output_type=TeachingAction,
    instructions=(
        "You are the GoalCoach Teaching Agent for beginner HSK1 Chinese. "
        "Your responsibility is to choose the NEXT pedagogical action, "
        "not to manage the whole curriculum and not to calculate mastery. "

        "Choose exactly one action: explain, ask, hint, or remediate. "

        "Ground teaching decisions in the curriculum using "
        "`search_hsk_curriculum` when necessary. "

        "Keep explanations concise and appropriate for the learner's HSK level. "
        "Provide Pinyin when helpful. "

        "Treat grading results as the source of truth for learner performance. "

        "If the learner has difficulty or failed the previous task, "
        "prefer hint or remediate. "

        "When action_type is 'ask', you MUST provide an Exercise "
        "and set expected_response to true. "

        "When action_type is not 'ask', exercise must be null."
    ),
)

teaching_agent.tool(search_hsk_curriculum)


@teaching_agent.instructions
async def add_learner_context(ctx: RunContext[AgentDeps]) -> str:
    """Inject relevant learner state into each teaching decision."""

    state = ctx.deps.learner_state

    target_level = (
        state.goal.target_hsk_level
        if state.goal
        else 1
    )

    recent_errors = [
        error.code
        for error in state.error_profile[-3:]
    ]

    return (
        f"Target HSK level: {target_level}. "
        f"Recent learner errors: {recent_errors or 'None'}."
    )
# instructions vs system_prompt vs prompt

# ---------------------------------------------------------------------------
# Teaching decision
# ---------------------------------------------------------------------------

async def next_teaching_action(
    deps: AgentDeps,
    session: TeachingSession,
) -> tuple[TeachingAction, str]:

    recent_turns = session.turns[-3:]

    history = "\n".join(
        (
            f"Action: {turn.action.action_type}\n"
            f"Content: {turn.action.content}\n"
            f"Learner response: {turn.learner_response or 'None'}\n"
            f"Grading result: {turn.grading_result or 'None'}"
        )
        for turn in recent_turns
    )

    prompt = f"""
Current concept:
{session.concept_id}

Recent teaching history:
{history or "No previous teaching turns."}

Select the single best NEXT teaching action.
Stay focused on concept {session.concept_id}.
"""

    result, provider = await run_with_fallback(
        teaching_agent,
        prompt,
        deps=deps,
    )

    return result.output, provider
