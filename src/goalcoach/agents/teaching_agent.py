"""Teaching Agent implemented with PydanticAI.

Answers: 'Given the active concept, learner error history, and failed attempts, how should we teach right now?'
Selects adaptive pedagogical modalities (EXPLANATION, HINT, CONTRAST_EXAMPLE, EXERCISE, RETRY)
based on student confusion and error profile.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from goalcoach.domain.enums import TeachingActionKind
from goalcoach.domain.models import LearnerState, TeachingAction
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    get_openrouter_model,
    run_with_fallback,
)
from goalcoach.infrastructure.persistence.content_service import ContentService

logger = logging.getLogger(__name__)


@dataclass
class TeachingDeps:
    """Dependencies injected into the Teaching Agent."""

    state: LearnerState
    content_service: ContentService
    concept_id: str
    failed_attempts: int = 0
    learner_query: str | None = None


TEACHING_SYSTEM_PROMPT = """You are the GoalCoach Adaptive Chinese Tutor for HSK1 learners.
You teach strictly within the verified HSK1 curriculum boundaries.

Core Pedagogical Invariant:
Same concept + different error history -> different instructional action.

Modality Selection Rules:
1. Fresh Encounter (failed_attempts == 0):
   - Choose `EXPLANATION` or `DIALOGUE`.
   - Provide a clear, bite-sized explanation. Always include Chinese characters (Hanzi), accurate tone-marked Pinyin, and English meaning.
   - If the learner has context interests (e.g., travel, food, business), weave them into the example sentences!
2. First Confusion / Help Requested (failed_attempts == 1 or learner asking for help):
   - Switch strategy! Do NOT simply repeat the same explanation.
   - Choose `HINT` or `CONTRAST_EXAMPLE`.
   - For particle/grammar issues (like 吗, 呢, 了 or word order), highlight the contrast between a statement and a question or provide an intuitive structural cue.
3. Multiple Failures (failed_attempts >= 2):
   - Choose `RETRY` or `EXERCISE`.
   - Provide a simplified fill-in-the-blank or scaffolded prompt to rebuild confidence.

Output Format:
Emit a structured `TeachingAction` containing:
- `action_kind`: The chosen modality tag.
- `concept_id`: The canonical concept tag being taught.
- `content`: The bilingual text shown to the student.
- `pinyin`: Tone-marked Pinyin for any Chinese characters.
- `exercise_payload`: Optional dictionary with exercise details if presenting a question.
"""

teaching_agent = Agent(
    model=get_openrouter_model(),
    deps_type=TeachingDeps,
    output_type=TeachingAction,
    system_prompt=TEACHING_SYSTEM_PROMPT,
)


@teaching_agent.tool
def get_concept_details(ctx: RunContext[TeachingDeps], concept_id: str) -> dict[str, Any]:
    """Retrieve title, communicative goal, grammar focus, and difficulty for the active concept."""
    concept = ctx.deps.content_service.get_concept(concept_id)
    if not concept:
        return {"error": f"Concept {concept_id} not found in Database #1"}
    return {
        "concept_id": concept.concept_id,
        "title_zh": concept.title_zh,
        "title_en": concept.title_en,
        "communicative_goal": concept.communicative_goal,
        "grammar_focus": concept.grammar_focus,
        "vocabulary_focus": concept.vocabulary_focus,
    }


@teaching_agent.tool
def get_teaching_cards(ctx: RunContext[TeachingDeps], concept_id: str) -> list[dict[str, Any]]:
    """Retrieve reviewed canonical teaching cards, explanations, and examples for the concept."""
    cards = ctx.deps.content_service.get_teaching_cards(concept_id)
    return [
        {
            "card_id": c.card_id,
            "card_type": c.card_type,
            "prompt_zh": c.prompt_zh,
            "pinyin": c.pinyin,
            "meaning_en": c.meaning_en,
            "explanation_en": c.explanation_en,
            "example_zh": c.example_zh,
            "example_pinyin": c.example_pinyin,
            "example_en": c.example_en,
        }
        for c in cards
    ]


class TeachingWorker:
    """Wrapper managing teaching agent invocation, strategy adaptation, and heuristic fallback."""

    def __init__(self, agent: Agent = teaching_agent) -> None:
        self.agent = agent

    async def teach_concept(
        self,
        concept_id: str,
        state: LearnerState,
        content_service: ContentService,
        failed_attempts: int = 0,
        learner_query: str | None = None,
    ) -> TeachingAction:
        """Adapts pedagogical strategy based on concept cards, student errors, and failed attempts."""
        deps = TeachingDeps(
            state=state,
            content_service=content_service,
            concept_id=concept_id,
            failed_attempts=failed_attempts,
            learner_query=learner_query,
        )

        relevant_errors = [
            err.code for err in state.error_profile if err.concept_id == concept_id
        ]
        interests_str = ", ".join(state.context_interests) if state.context_interests else "general"

        prompt = (
            f"Active Concept: {concept_id}\n"
            f"Failed Attempts on this concept: {failed_attempts}\n"
            f"Recurring Error Codes: {relevant_errors}\n"
            f"Learner Interests: {interests_str}\n"
            f"Learner Query / Context: {learner_query or 'Normal lesson progression'}\n"
            "Emit the optimal TeachingAction for this turn."
        )

        try:
            result, _ = await run_with_fallback(self.agent, prompt, deps=deps)
            action: TeachingAction = result.output
            if action.concept_id == concept_id and action.content:
                return action
        except Exception as exc:
            logger.warning("TeachingAgent LLM execution failed (%s); using heuristic fallback.", exc)

        return self._heuristic_fallback(concept_id, state, content_service, failed_attempts, learner_query)

    def _heuristic_fallback(
        self,
        concept_id: str,
        state: LearnerState,
        content_service: ContentService,
        failed_attempts: int,
        learner_query: str | None,
    ) -> TeachingAction:
        """Deterministic strategy fallback based on state and attempt counts."""
        concept = content_service.get_concept(concept_id)
        cards = content_service.get_teaching_cards(concept_id)
        title_zh = concept.title_zh if concept else "你好"
        title_en = concept.title_en if concept else "Hello"

        card = cards[0] if cards else None
        pinyin = card.pinyin if card and card.pinyin else "nǐ hǎo"
        example_zh = card.example_zh if card and card.example_zh else title_zh
        example_pinyin = card.example_pinyin if card and card.example_pinyin else pinyin
        example_en = card.example_en if card and card.example_en else title_en

        if failed_attempts == 0:
            # Standard Explanation
            interests = f" (Focus: {', '.join(state.context_interests)})" if state.context_interests else ""
            content = (
                f"Let's learn **{title_zh}** ({title_en}){interests}!\n\n"
                f"**Pattern / Example:** {example_zh}\n"
                f"*Pinyin:* {example_pinyin}\n"
                f"*Meaning:* {example_en}\n\n"
                "Try forming a sentence using this pattern!"
            )
            return TeachingAction(
                action_kind=TeachingActionKind.EXPLANATION,
                concept_id=concept_id,
                content=content,
                pinyin=example_pinyin,
            )
        elif failed_attempts == 1:
            # Contrast Example or Hint
            content = (
                f"**Coach Hint for {title_zh}:**\n\n"
                f"Remember the key structure: In Chinese, yes/no questions simply place **吗 (ma)** "
                f"at the very end of a statement without changing the word order!\n\n"
                f"**Example:**\n"
                f"• Statement: 你是老师。 (Nǐ shì lǎoshī - You are a teacher.)\n"
                f"• Question: 你是老师**吗**？ (Nǐ shì lǎoshī **ma**? - Are you a teacher?)"
            )
            return TeachingAction(
                action_kind=TeachingActionKind.CONTRAST_EXAMPLE,
                concept_id=concept_id,
                content=content,
                pinyin="ma?",
            )
        else:
            # Retry / Simplified scaffold
            content = (
                "Let's simplify! Fill in the blank to ask 'Are you busy?':\n\n"
                "你忙 ___ ？\n"
                "(Hint: Use the question particle you just learned!)"
            )
            return TeachingAction(
                action_kind=TeachingActionKind.RETRY,
                concept_id=concept_id,
                content=content,
                pinyin="Nǐ máng ___ ?",
                exercise_payload={"type": "fill_blank", "target": "吗"},
            )


# --- Legacy Compatibility Interface ---


class TutorResponse(BaseModel):
    """Backwards-compatible legacy tutor response structure."""

    reply: str = Field(default="", description="Explanations, exercises, or feedback with Pinyin")
    grammar_points: list[str] = Field(default_factory=list)
    suggested_practice: str | None = Field(default=None)
    concept_id: str = Field(default="hsk1_c01")
    is_evaluating_answer: bool = Field(default=False)
    passed: bool | None = Field(default=None)
    hint_given: bool = Field(default=False)


tutor_agent = Agent(
    model=get_openrouter_model(),
    output_type=TutorResponse,
    system_prompt="You are the GoalCoach Chinese Teacher, an adaptive HSK1 Chinese tutor.",
)


async def chat_with_tutor(deps: Any, user_message: str) -> tuple[TutorResponse, str]:
    """Legacy helper for conversational tutoring."""
    result, provider = await run_with_fallback(tutor_agent, user_message, deps=deps)
    return result.output, provider


__all__ = [
    "TEACHING_SYSTEM_PROMPT",
    "TeachingDeps",
    "TeachingWorker",
    "TutorResponse",
    "chat_with_tutor",
    "teaching_agent",
    "tutor_agent",
]