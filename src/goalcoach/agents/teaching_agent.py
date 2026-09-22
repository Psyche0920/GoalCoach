"""Teaching Agent implemented with PydanticAI.

Answers: 'Given the active concept, learner error history, and failed attempts, how should we teach right now?'
Selects adaptive pedagogical modalities (EXPLANATION, HINT, CONTRAST_EXAMPLE, EXERCISE, RETRY)
based on student confusion and error profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext

from goalcoach.application.agent_history import format_agent_history
from goalcoach.domain.enums import TeachingActionKind
from goalcoach.domain.models import LearnerState, TeachingAction
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    AgentOutputError,
    LLMUnavailableError,
    get_openrouter_model,
    get_output_retries,
    run_with_fallback,
)
from goalcoach.infrastructure.persistence.content_service import ContentService


@dataclass
class TeachingDeps:
    """Dependencies injected into the Teaching Agent."""

    state: LearnerState
    content_service: ContentService
    concept_id: str
    failed_attempts: int = 0
    learner_query: str | None = None
    excluded_exercise_id: str | None = None


TEACHING_SYSTEM_PROMPT = """You are the GoalCoach Adaptive Chinese Tutor for Chinese learning beginners.
You teach strictly within the verified HSK curriculum boundaries.

Core Pedagogical Invariant:
Same concept + different error history -> different instructional action.

Cross-Session Continuity:
- Treat the compact learning history as advisory evidence, not a ban on repetition.
- Do not reproduce prior wording or an identical exercise unless repetition is pedagogically justified.
- When revisiting a concept, adapt the explanation or practice using its prior outcome and errors.

Goal Grounding:
- The learner's complete free-form goal is the authoritative teaching context.
- Interpret that goal directly when choosing examples and communicative situations.
- Do not invent material beyond the verified curriculum cards and exercises.

Modality Selection Rules:
1. Fresh Encounter (failed_attempts == 0):
   - Choose `EXPLANATION` or `DIALOGUE`.
   - Provide a clear, bite-sized explanation. You MUST present the target vocabulary or sentence structure using a Markdown table with the exact columns:
     | Character | Pinyin | Meaning |
     | :--- | :--- | :--- |
     | <Hanzi> | <tone-marked pinyin> | <English meaning> |
   - Adapt examples directly to the learner's free-form goal when it fits the active concept.
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
- `history_summary`: A self-contained semantic summary, in one or two complete English sentences and no more than 240 characters. State what was taught, the teaching strategy, and the practice objective. Do not merely copy the beginning of `content`.
- `pinyin`: Tone-marked Pinyin for any Chinese characters.

Language Requirements (STRICT):
- Instructional Medium: English ONLY unless the learners ask you to teach in other languages. All grammar explanations, instructions, guidelines, hints, structural breakdowns, and feedback MUST be written in English.
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
        excluded_exercise_id: str | None = None,
    ) -> TeachingAction:
        """Adapts pedagogical strategy based on concept cards, student errors, and failed attempts."""
        deps = TeachingDeps(
            state=state,
            content_service=content_service,
            concept_id=concept_id,
            failed_attempts=failed_attempts,
            learner_query=learner_query,
            excluded_exercise_id=excluded_exercise_id,
        )

        relevant_errors = [err.code for err in state.error_profile if err.concept_id == concept_id]
        history_summary = format_agent_history(state)
        prompt = (
            f"Active Concept: {concept_id}\n"
            f"Learner Goal: {state.goal.title if state.goal else 'General HSK1 Chinese'}\n"
            f"Failed Attempts on this concept: {failed_attempts}\n"
            f"Recurring Error Codes: {relevant_errors}\n"
            f"Learner Query / Context: {learner_query or 'Normal lesson progression'}\n"
            f"Exercise to replace: {excluded_exercise_id or 'None'}\n"
            f"Recent Cross-Session Learning History:\n{history_summary}\n"
            "Emit the optimal TeachingAction for this turn."
        )

        try:
            result, provider = await run_with_fallback(
                self.agent,
                prompt,
                deps=deps,
                component="teaching_agent",
            )
            action: TeachingAction = result.output
            action.metadata.update(
                {
                    "provider": provider,
                    "fallback_used": provider.startswith("ollama:"),
                    "notice": (
                        "The primary model was unavailable; the configured fallback model was used."
                        if provider.startswith("ollama:")
                        else None
                    ),
                }
            )
            if action.concept_id == concept_id and action.content:
                return self._attach_curriculum_exercise(
                    action,
                    content_service,
                    state=state,
                    is_remedial=(failed_attempts > 0),
                    excluded_exercise_id=excluded_exercise_id,
                )
        except LLMUnavailableError as exc:
            action = self._deterministic_fallback(
                concept_id,
                state,
                content_service,
                failed_attempts,
                notice=f"LLM unavailable; deterministic teaching fallback used: {exc}",
            )
            return self._attach_curriculum_exercise(
                action,
                content_service,
                state=state,
                is_remedial=failed_attempts > 0,
                excluded_exercise_id=excluded_exercise_id,
            )
        action = self._deterministic_fallback(
            concept_id,
            state,
            content_service,
            failed_attempts,
            notice="Teaching Agent returned an invalid action; deterministic fallback used.",
        )
        return self._attach_curriculum_exercise(
            action,
            content_service,
            state=state,
            is_remedial=failed_attempts > 0,
            excluded_exercise_id=excluded_exercise_id,
        )

    @staticmethod
    def _attach_curriculum_exercise(
        action: TeachingAction,
        content_service: ContentService,
        state: LearnerState | None = None,
        is_remedial: bool = False,
        excluded_exercise_id: str | None = None,
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
        recent = (
            {
                turn.exercise_id
                for turn in state.agent_history.recent_teaching_turns
                if turn.concept_id == action.concept_id and turn.exercise_id
            }
            if state
            else set()
        )
        excluded = {excluded_exercise_id} if excluded_exercise_id else set()

        if is_remedial:
            # In remediation: prioritize unattempted exercises (neither completed nor failed today)
            candidates = [
                e
                for e in all_exercises
                if e.exercise_id not in completed
                and e.exercise_id not in mistakes
                and e.exercise_id not in recent
                and e.exercise_id not in excluded
            ]
            if not candidates:
                candidates = [
                    e
                    for e in all_exercises
                    if e.exercise_id not in completed
                    and e.exercise_id not in recent
                    and e.exercise_id not in excluded
                ]
            if not candidates:
                candidates = [
                    e
                    for e in all_exercises
                    if e.exercise_id not in completed and e.exercise_id not in excluded
                ]
            selected = candidates[0] if candidates else all_exercises[0]
        else:
            uncompleted = [
                e
                for e in all_exercises
                if e.exercise_id not in completed
                and e.exercise_id not in recent
                and e.exercise_id not in excluded
            ]
            if not uncompleted:
                uncompleted = [
                    e
                    for e in all_exercises
                    if e.exercise_id not in completed and e.exercise_id not in excluded
                ]
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

    @staticmethod
    def _deterministic_fallback(
        concept_id: str,
        state: LearnerState,
        content_service: ContentService,
        failed_attempts: int,
        *,
        notice: str,
    ) -> TeachingAction:
        """Build a transparent fallback solely from canonical curriculum material."""
        concept = content_service.get_concept(concept_id)
        cards = content_service.get_teaching_cards(concept_id)
        if concept is None or not cards:
            raise AgentOutputError(f"No canonical teaching material exists for {concept_id}")
        card = cards[0]
        if failed_attempts == 0:
            action_kind = TeachingActionKind.EXPLANATION
            strategy = "a concise canonical explanation"
        elif failed_attempts == 1:
            action_kind = TeachingActionKind.CONTRAST_EXAMPLE
            strategy = "a different curriculum example after confusion"
        else:
            action_kind = TeachingActionKind.RETRY
            strategy = "a simplified retry grounded in one curriculum example"
        goal = state.goal.title if state.goal else "HSK1 communication"
        content = (
            f"Goal context: {goal}\n\n"
            f"| Character | Pinyin | Meaning |\n"
            f"| :--- | :--- | :--- |\n"
            f"| {card.example_zh or card.prompt_zh} | "
            f"{card.example_pinyin or card.pinyin or ''} | "
            f"{card.example_en or card.meaning_en or ''} |\n\n"
            f"{card.explanation_en or concept.communicative_goal}"
        )
        return TeachingAction(
            action_kind=action_kind,
            concept_id=concept_id,
            content=content,
            history_summary=f"Taught {concept.title_en} using {strategy} for the learner goal.",
            pinyin=card.example_pinyin or card.pinyin,
            metadata={
                "provider": "deterministic",
                "fallback_used": True,
                "notice": notice,
            },
        )

__all__ = [
    "TEACHING_SYSTEM_PROMPT",
    "TeachingDeps",
    "TeachingWorker",
    "teaching_agent",
]
