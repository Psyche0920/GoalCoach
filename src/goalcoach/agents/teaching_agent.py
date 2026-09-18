"""Teaching Agent implemented with PydanticAI.

Answers: 'Given the active concept, learner error history, and failed attempts, how should we teach right now?'
Selects adaptive pedagogical modalities (EXPLANATION, HINT, CONTRAST_EXAMPLE, EXERCISE, RETRY)
based on student confusion and error profile.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext

from goalcoach.domain.enums import TeachingActionKind
from goalcoach.domain.models import LearnerState, TeachingAction
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    get_openrouter_model,
    get_output_retries,
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
   - Provide a clear, bite-sized explanation. You MUST present the target vocabulary or sentence structure using a Markdown table with the exact columns:
     | Character | Pinyin | Meaning |
     | :--- | :--- | :--- |
     | <Hanzi> | <tone-marked pinyin> | <English meaning> |
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
- `content`: The teaching text shown to the student. For explanations, it MUST include the Markdown table (`| Character | Pinyin | Meaning |`).
- `pinyin`: Tone-marked Pinyin for any Chinese characters.

Language Requirements (STRICT):
- Instructional Medium: English ONLY. All grammar explanations, instructions, guidelines, hints, structural breakdowns, and feedback MUST be written in English.
- Target Language: Mandarin Chinese. Chinese characters (Hanzi) and Pinyin are ONLY permitted as specific vocabulary examples, patterns, or target exercise items—NEVER as the explanatory language.

Explanation and exercises should be strongly relevant.
"""

teaching_agent = Agent(
    model=get_openrouter_model(),
    deps_type=TeachingDeps,
    output_type=TeachingAction,
    output_retries=get_output_retries(),
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

        relevant_errors = [err.code for err in state.error_profile if err.concept_id == concept_id]
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
                return self._attach_curriculum_exercise(
                    action, content_service, state=state, is_remedial=(failed_attempts > 0)
                )
        except Exception as exc:
            logger.warning(
                "TeachingAgent LLM execution failed (%s); using heuristic fallback.", exc
            )

        fallback = self._heuristic_fallback(
            concept_id,
            state,
            content_service,
            failed_attempts,
            learner_query,
        )
        return self._attach_curriculum_exercise(
            fallback, content_service, state=state, is_remedial=(failed_attempts > 0)
        )

    @staticmethod
    def _attach_curriculum_exercise(
        action: TeachingAction,
        content_service: ContentService,
        state: LearnerState | None = None,
        is_remedial: bool = False,
    ) -> TeachingAction:
        """Attach a canonical exercise without exposing its accepted answers, rotating on completion or failure."""
        all_exercises = content_service.get_exercises_for_concept(
            action.concept_id,
            limit=10,
            randomize=False,
        )
        if not all_exercises:
            raise LookupError(f"No curriculum exercise found for concept {action.concept_id}")

        completed = set(state.today_completed_exercise_ids) if state else set()
        mistakes = set(state.today_mistake_exercise_ids) if state else set()

        if is_remedial:
            # In remediation: prioritize unattempted exercises (neither completed nor failed today)
            candidates = [
                e
                for e in all_exercises
                if e.exercise_id not in completed and e.exercise_id not in mistakes
            ]
            if not candidates:
                # If all exercises have been attempted, pick one not yet completed
                candidates = [e for e in all_exercises if e.exercise_id not in completed]
            selected = candidates[0] if candidates else all_exercises[0]
        else:
            uncompleted = [e for e in all_exercises if e.exercise_id not in completed]
            selected = uncompleted[0] if uncompleted else all_exercises[0]

        payload = dict(action.exercise_payload or {})
        payload.update(
            {
                "exercise_id": selected.exercise_id,
                "concept_id": selected.concept_id,
                "prompt": selected.prompt,
                "instruction": selected.instruction or "",
            }
        )
        action.exercise_payload = payload
        return action

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
            interests = (
                f" (Focus: {', '.join(state.context_interests)})" if state.context_interests else ""
            )
            content = (
                f"Let's learn **{title_zh}** ({title_en}){interests}!\n\n"
                f"| Character | Pinyin | Meaning |\n"
                f"| :--- | :--- | :--- |\n"
                f"| {example_zh} | {example_pinyin} | {example_en} |\n\n"
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


__all__ = [
    "TEACHING_SYSTEM_PROMPT",
    "TeachingDeps",
    "TeachingWorker",
    "teaching_agent",
]
