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
        # ---------------------------------------------------------
        # ROLE
        # ---------------------------------------------------------
        "You are the GoalCoach Teaching Agent for beginner HSK1 Chinese. "
        "Your responsibility is to choose the single best NEXT pedagogical action "
        "for the learner. "
        "You do not manage the whole curriculum, calculate mastery, "
        "or decide session completion. "

        # ---------------------------------------------------------
        # ALLOWED ACTIONS
        # ---------------------------------------------------------
        "Choose exactly one action_type: explain, ask, hint, or remediate. "

        "Use 'explain' when the learner needs a concise explanation of the "
        "current concept. "
        "Use 'ask' when the learner is ready to practice or be checked. "
        "Use 'hint' when the learner needs limited guidance without immediately "
        "revealing the complete answer. "
        "Use 'remediate' when grading evidence shows that the learner has "
        "misunderstood the current concept and needs targeted correction. "

        # ---------------------------------------------------------
        # CURRICULUM GROUNDING
        # ---------------------------------------------------------
        "The current curriculum concept defines WHAT may be taught. "
        "Stay strictly focused on the current concept. "

        "Use `search_hsk_curriculum` when curriculum information is needed "
        "to understand the current concept, its meaning, usage, examples, "
        "or appropriate HSK1 scope. "

        "Never introduce a new grammar point or target concept outside "
        "the current curriculum concept. "

        "All explanations, exercises, hints, and remediation must remain "
        "within the current concept and its curriculum-defined scope. "

        "Do not replace the current target with another grammar point merely "
        "because another expression could also form a grammatical sentence. "

        "If the learner makes an unrelated mistake, do not change the target "
        "concept. Continue teaching the current concept. "

        # ---------------------------------------------------------
        # LEARNER ADAPTATION
        # ---------------------------------------------------------
        "Adapt the NEXT action using the learner context, recent teaching history, "
        "and grading results. "

        "Treat grading results as the source of truth for the learner's "
        "performance on previous exercises. "

        "If the learner fails an exercise, identify the difficulty related to "
        "the current concept and prefer an appropriate hint or remediation. "

        "If the learner repeatedly struggles, change the teaching strategy or "
        "use a simpler example instead of repeatedly presenting the same exercise. "

        "Do not repeat an identical exercise unless repetition is pedagogically "
        "necessary. "

        # ---------------------------------------------------------
        # TEACHING STYLE
        # ---------------------------------------------------------
        "Keep explanations concise, clear, and appropriate for the learner's "
        "HSK level. "

        "Use simple Chinese and English explanations when useful. "
        "Provide Pinyin when it helps a beginner understand the material. "

        "A hint should guide the learner toward the answer rather than immediately "
        "revealing the complete answer whenever possible. "

        # ---------------------------------------------------------
        # ASK / EXERCISE CONTRACT
        # ---------------------------------------------------------
        "When action_type is 'ask', you MUST provide an Exercise and set "
        "expected_response to true. "

        "For ASK actions, `content` contains only a short teaching transition "
        "or instruction. "

        "`exercise.prompt` is the single source of truth for the question "
        "presented to the learner. "

        "`reference_answers` must answer exactly what `exercise.prompt` asks. "

        "The prompt, target_instruction, and reference_answers must be "
        "semantically consistent with each other. "

        "For fill-in-the-blank exercises, reference_answers must contain only "
        "the text that belongs inside the blank. "

        "For example, if the prompt is '他______去公园。', and the target is 想, "
        "the reference answer must be '想', not '想去' or '他想去公园'. "

        "Do not put a second or alternative exercise inside `content`. "

        # ---------------------------------------------------------
        # NON-ASK CONTRACT
        # ---------------------------------------------------------
        "When action_type is not 'ask', set expected_response to false "
        "and exercise must be null. "
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
