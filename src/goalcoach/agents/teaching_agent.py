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


TEACHING_SYSTEM_PROMPT = """You are Coach Baobao, the warm, encouraging, and adaptive Chinese Tutor.
You teach strictly within verified curriculum boundaries with clarity, empathy, and high pedagogical precision.

Core Pedagogical Philosophy:
Same concept + different error history -> different instructional action.
- Tone & Persona: Supportive, observant, and humane. Greet the learner warmly, celebrate their efforts, and explain grammatical ideas in simple, intuitive terms. Avoid cold, robotic statements.
- Strict Grounding: The student is about to practice an actual target exercise (specified in Target Upcoming Practice). Your explanation or guidance MUST directly bridge to and prepare the student for this specific practice task!
- Never Abandon the Learner: Even during retries or multiple failures, NEVER throw a naked exercise without guidance. Always deconstruct the concept step-by-step with empathy.

Pedagogical Modality Rules:
1. Fresh Encounter (failed_attempts == 0):
   - Choose `EXPLANATION` or `DIALOGUE`.
   - Provide a warm, conversational intro connecting to the communicative goal.
   - Present the target vocabulary or sentence structure using a clear Markdown table with the exact columns:
     | Character | Pinyin | Meaning |
     | :--- | :--- | :--- |
     | <Hanzi> | <tone-marked pinyin> | <English meaning> |
   - Provide 1 natural example sentence tailored to the upcoming practice task and learner interests (e.g. food, travel, business).
   - Conclude with an encouraging prompt introducing the upcoming practice.

2. First Confusion / Help Requested (failed_attempts == 1 or learner query):
   - Choose `HINT` or `CONTRAST_EXAMPLE`.
   - Validate the student's effort empathetically ("That was a great try!").
   - Highlight the precise contrast (e.g., statement vs. question word order, or 吗 vs. 呢). Give an intuitive rule-of-thumb.
   - Do NOT just repeat the earlier explanation.

3. Multiple Failures (failed_attempts >= 2):
   - Choose `RETRY` or `CONTRAST_EXAMPLE`.
   - Provide gentle, compassionate scaffolding: break down the target pattern into tiny bite-sized pieces (e.g., Subject + Verb + Particle).
   - Reassure the learner, highlight where the key word goes, and guide them into the retry.

Output Format:
Emit a structured `TeachingAction` containing:
- `action_kind`: The chosen modality tag.
- `concept_id`: The canonical concept tag being taught.
- `content`: The teaching text shown to the student. For explanations, it MUST include the Markdown table (`| Character | Pinyin | Meaning |`).
- `pinyin`: Tone-marked Pinyin for any Chinese characters.

Language Requirements (STRICT):
- Instructional Medium: English ONLY. All grammar explanations, instructions, guidelines, hints, structural breakdowns, and feedback MUST be written in English. You are teaching absolute beginners. Do NOT converse in Chinese.
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
        is_remedial = failed_attempts > 0
        candidate_exercise = self._select_candidate_exercise(
            concept_id, content_service, state=state, is_remedial=is_remedial
        )

        deps = TeachingDeps(
            state=state,
            content_service=content_service,
            concept_id=concept_id,
            failed_attempts=failed_attempts,
            learner_query=learner_query,
        )

        relevant_errors = [
            err.code for err in state.error_profile if err.concept_id == concept_id]
        interests_str = ", ".join(
            state.context_interests) if state.context_interests else "general"

        options_hint = ""
        if getattr(candidate_exercise, "options", None):
            options_hint = f"\nUpcoming Practice Options: {candidate_exercise.options}"

        ex_type = getattr(candidate_exercise, "exercise_type", "mcq")
        prompt = (
            f"Active Concept: {concept_id}\n"
            f"Failed Attempts on this concept: {failed_attempts}\n"
            f"Target Upcoming Practice Type: {ex_type}\n"
            f"Target Upcoming Practice: {candidate_exercise.instruction or ''} -> {candidate_exercise.prompt}"
            f"{options_hint}\n"
            f"Learner Interests: {interests_str}\n"
            f"Learner Query / Context: {learner_query or 'Normal lesson progression'}\n"
            "Emit the optimal TeachingAction for this turn. Ground your explanation or guidance directly to help the student succeed on this upcoming practice task.\n"
            "CRITICAL:\n"
            "1. Write all explanations and conversational text in ENGLISH. Do not explain in Chinese.\n"
            "2. Keep it ultra-concise (under 60 words for fresh explanations, under 40 words for hints/retries). Do NOT write long essays."
        )

        try:
            result, _ = await run_with_fallback(self.agent, prompt, deps=deps)
            action: TeachingAction = result.output
            if action.concept_id == concept_id and action.content:
                return self._attach_selected_exercise(action, candidate_exercise)
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
            candidate_exercise=candidate_exercise,
        )
        return self._attach_selected_exercise(fallback, candidate_exercise)

    @staticmethod
    def _select_candidate_exercise(
        concept_id: str,
        content_service: ContentService,
        state: LearnerState | None = None,
        is_remedial: bool = False,
    ) -> Any:
        """Select the target exercise before agent invocation to ensure grounded teaching."""
        all_exercises = content_service.get_exercises_for_concept(
            concept_id,
            limit=10,
            randomize=False,
        )
        if not all_exercises:
            raise LookupError(
                f"No curriculum exercise found for concept {concept_id}")

        completed = set(state.today_completed_exercise_ids) if state else set()
        mistakes = set(state.today_mistake_exercise_ids) if state else set()

        if is_remedial:
            candidates = [
                e
                for e in all_exercises
                if e.exercise_id not in completed and e.exercise_id not in mistakes
            ]
            if not candidates:
                candidates = [
                    e for e in all_exercises if e.exercise_id not in completed]
            return candidates[0] if candidates else all_exercises[0]
        else:
            uncompleted = [
                e for e in all_exercises if e.exercise_id not in completed]
            return uncompleted[0] if uncompleted else all_exercises[0]

    @staticmethod
    def _attach_selected_exercise(
        action: TeachingAction,
        selected: Any,
    ) -> TeachingAction:
        """Attach a canonical exercise without exposing its accepted answers."""
        payload = dict(action.exercise_payload or {})
        payload.update(
            {
                "exercise_id": selected.exercise_id,
                "concept_id": selected.concept_id,
                "exercise_type": getattr(selected, "exercise_type", "unknown"),
                "prompt": selected.prompt,
                "instruction": selected.instruction or "",
                "options": getattr(selected, "options", None),
            }
        )
        action.exercise_payload = payload
        return action

    @staticmethod
    def _attach_curriculum_exercise(
        action: TeachingAction,
        content_service: ContentService,
        state: LearnerState | None = None,
        is_remedial: bool = False,
    ) -> TeachingAction:
        """Backwards compatibility helper."""
        selected = TeachingWorker._select_candidate_exercise(
            action.concept_id, content_service, state=state, is_remedial=is_remedial
        )
        return TeachingWorker._attach_selected_exercise(action, selected)

    def _heuristic_fallback(
        self,
        concept_id: str,
        state: LearnerState,
        content_service: ContentService,
        failed_attempts: int,
        learner_query: str | None,
        candidate_exercise: Any | None = None,
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

        target_prompt = getattr(candidate_exercise, "prompt", example_zh)
        target_inst = getattr(candidate_exercise, "instruction", "")

        if failed_attempts == 0:
            is_matching = getattr(candidate_exercise, "exercise_type", "") == "matching"
            if is_matching:
                content = (
                    f"Let's learn **{title_zh}** ({title_en})!\n\n"
                    f"Review the key words below, then connect each numbered Chinese word with its English meaning."
                )
            else:
                content = (
                    f"Let's explore **{title_zh}** ({title_en})!\n\n"
                    f"| Hanzi | Pinyin | Meaning |\n"
                    f"| :--- | :--- | :--- |\n"
                    f"| {example_zh} | {example_pinyin} | {example_en} |\n\n"
                    f"Let's put this into practice below!"
                )
            return TeachingAction(
                action_kind=TeachingActionKind.EXPLANATION,
                concept_id=concept_id,
                content=content,
                pinyin=example_pinyin,
            )
        elif failed_attempts == 1:
            # Contrast Example or Hint - empathetic validation and clear contrast cue
            content = (
                f"Good effort! Let's look at **{title_zh}** from a slightly different angle.\n\n"
                f"**Coach Tip:** In Chinese, sentence structure often stays very straightforward. "
                f"Pay attention to the key words and particles:\n\n"
                f"• Focus item: **{example_zh}** ({example_pinyin}) — {example_en}\n"
                f"• Rule of thumb: Check the exact word order and meaning before answering.\n\n"
                f"Take a breath and give it another try below!"
            )
            return TeachingAction(
                action_kind=TeachingActionKind.CONTRAST_EXAMPLE,
                concept_id=concept_id,
                content=content,
                pinyin=example_pinyin,
            )
        else:
            # Retry / Simplified scaffold - gentle deconstruction, no cold sentences
            content = (
                f"Don't worry, mastering Chinese takes patience! Let's break this down step-by-step.\n\n"
                f"For this question, remember:\n"
                f"1. What are we looking for? **{title_zh}** ({title_en}).\n"
                f"2. Look for the key element: `{example_zh}` ({example_pinyin}).\n\n"
                f"You've got this! Choose or complete the correct option below."
            )
            return TeachingAction(
                action_kind=TeachingActionKind.RETRY,
                concept_id=concept_id,
                content=content,
                pinyin=example_pinyin,
            )


# --- Legacy Compatibility Interface ---


class TutorResponse(BaseModel):
    """Backwards-compatible legacy tutor response structure."""

    reply: str = Field(
        default="", description="Explanations, exercises, or feedback with Pinyin")
    grammar_points: list[str] = Field(default_factory=list)
    suggested_practice: str | None = Field(default=None)
    concept_id: str = Field(default="hsk1_c01")
    is_evaluating_answer: bool = Field(default=False)
    passed: bool | None = Field(default=None)
    hint_given: bool = Field(default=False)


tutor_agent = Agent(
    model=get_openrouter_model(),
    output_type=TutorResponse,
    output_retries=get_output_retries(),
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
