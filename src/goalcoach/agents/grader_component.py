"""Grader Component: Stateless evaluator combining deterministic fast-paths with 3-axis LLM rubric scoring.

Implements PRD Section 10:
1. Deterministic fast-path match against accepted reference answers (bypasses LLM in <5ms).
2. PydanticAI evaluation against 3 axes: grammatical_correctness, semantic_precision, pragmatic_appropriateness.
3. Strict gate evaluation: passed_gates is True iff grammatical >= 0.70 and semantic >= 0.70.
4. Specific taxonomy error tagging (ERR_QUESTION_MA, ERR_WORD_ORDER, ERR_MODAL_HUI, etc.).
"""

from __future__ import annotations

from uuid import uuid4

from pydantic_ai import Agent

from goalcoach.domain.models import (
    Exercise,
    GradingResult,
    RubricScores,
)
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    LLMUnavailableError,
    get_openrouter_model,
    get_output_retries,
    run_with_fallback,
)

GRADER_SYSTEM_PROMPT = """You are the GoalCoach Chinese Grading Evaluator.
Assess the learner's submission against the exercise prompt, instruction, and reference answers.

Evaluate along 3 distinct rubric axes (scores from 0.0 to 1.0):
1. `grammatical_correctness`: Word order, syntax, measure words, particle accuracy (吗, 呢, 了, 的), or language accuracy.
2. `semantic_precision`: Accuracy of intended meaning and STRICT task fulfillment.
3. `pragmatic_appropriateness`: Register and conversational naturalness.

Gate Rule:
- `passed_gates` must be True if and only if:
  `grammatical_correctness >= 0.70` AND `semantic_precision >= 0.70`.

Strict Task Alignment Rules:
- If the instruction asks for meaning or translation (e.g. "Choose the meaning", "Select the correct English translation", "Translate into English"), the learner MUST provide the English meaning/translation. Merely writing or transliterating the Chinese word in Pinyin (e.g., answering 'duoshao' when asked for the meaning of '多少') is a complete task failure: assign `semantic_precision < 0.30`, `passed_gates = False`, and tag `ERR_SEMANTIC`.
- If the exercise asks for a Chinese response, pinyin without tone marks is acceptable, but it must actually address the question asked.

Error Taxonomy Codes:
If there is a mistake, tag specific codes in `detected_errors`, such as:
- `ERR_SEMANTIC`: Answer fails to address the exercise instruction or target meaning.
- `ERR_QUESTION_MA`: Missing, misplaced, or redundant question particle 吗.
- `ERR_WORD_ORDER`: SVO order violations, time/place adverb placement.
- `ERR_MODAL_HUI`: Misuse of 会 vs 能 vs 可以.
- `ERR_PARTICLE_DE`: Misuse of possessive/attributive 的.
- `ERR_ASPECT_LE`: Incorrect completed action aspect marker 了.
- `ERR_VOCABULARY`: Incorrect vocabulary selection.

Provide encouraging, targeted, and factual feedback addressing the learner's mistake.
"""

grader_agent = Agent(
    model=get_openrouter_model(),
    output_type=GradingResult,
    output_retries=get_output_retries(),
    system_prompt=GRADER_SYSTEM_PROMPT,
)


class GraderComponent:
    """Stateless evaluator producing rubric grading evidence for the Progress Service."""

    def __init__(self, agent: Agent = grader_agent) -> None:
        self.agent = agent

    async def grade(
        self,
        exercise: Exercise,
        answer: str,
    ) -> GradingResult:
        """Evaluates submission against exercise rubrics with fast-path short-circuiting."""
        clean_student_ans = answer.strip()
        exercise_id = exercise.id or uuid4()

        # 1. Fast Path: Exact reference answer match (bypasses LLM, <5ms)
        accepted = [ans.strip() for ans in exercise.reference_answers if ans]
        if clean_student_ans in accepted:
            return GradingResult(
                exercise_id=exercise_id,
                scores=RubricScores(
                    grammatical_correctness=1.0,
                    semantic_precision=1.0,
                    pragmatic_appropriateness=1.0,
                ),
                passed_gates=True,
                confidence=1.0,
                feedback="Perfect! Your answer matches the accepted standard response.",
                detected_errors=[],
                grader_version="deterministic-fast-path",
                metadata={"provider": "deterministic", "fallback_used": False},
            )

        # 2. Heuristic check for common known errors if LLM fails
        prompt = (
            f"Exercise Prompt: {exercise.prompt}\n"
            f"Target Concept: {exercise.concept_id}\n"
            f"Instruction: {exercise.target_instruction}\n"
            f"Student Answer: {clean_student_ans}\n"
            f"Reference Answers: {', '.join(exercise.reference_answers)}\n"
            "Grade this response adhering strictly to the rubric and gating rules."
        )

        try:
            result, provider = await run_with_fallback(self.agent, prompt, deps=None)
            llm_result: GradingResult = result.output
            llm_result.exercise_id = exercise_id
            llm_result.metadata.update(
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

            # Deterministic gating guardrails:
            # If critical errors are detected, passed_gates must be False
            critical_prefixes = (
                "ERR_QUESTION_MA",
                "ERR_WORD_ORDER",
                "ERR_MODAL_HUI",
                "ERR_SEMANTIC",
                "ERR_VOCABULARY",
                "ERR_PRAGMATIC",
                "ERR_GRAMMAR",
            )
            has_critical_error = any(
                any(crit in err.upper() for crit in critical_prefixes)
                for err in llm_result.detected_errors
            )
            if has_critical_error or (
                llm_result.scores.grammatical_correctness < 0.70
                or llm_result.scores.semantic_precision < 0.70
            ):
                llm_result.passed_gates = False

            return llm_result
        except LLMUnavailableError as exc:
            return self._deterministic_fallback(
                exercise_id,
                notice=f"LLM unavailable; conservative deterministic grading fallback used: {exc}",
            )
        return self._deterministic_fallback(
            exercise_id,
            notice="Grader returned an invalid rubric result; deterministic fallback used.",
        )

    @staticmethod
    def _deterministic_fallback(exercise_id: object, *, notice: str) -> GradingResult:
        """Fail closed when a non-exact answer cannot be evaluated by an LLM."""
        return GradingResult(
            exercise_id=str(exercise_id),
            scores=RubricScores(
                grammatical_correctness=0.0,
                semantic_precision=0.0,
                pragmatic_appropriateness=0.0,
            ),
            passed_gates=False,
            confidence=0.0,
            feedback=(
                "This answer could not be evaluated by the language model. "
                "It was not counted as correct; please retry when model service is available."
            ),
            detected_errors=["ERR_GRADING_LLM_UNAVAILABLE"],
            grader_version="deterministic-fail-closed-fallback",
            metadata={
                "provider": "deterministic",
                "fallback_used": True,
                "notice": notice,
            },
        )

__all__ = [
    "GRADER_SYSTEM_PROMPT",
    "GraderComponent",
    "grader_agent",
]
