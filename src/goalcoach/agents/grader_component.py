"""Grader Component: Stateless evaluator combining deterministic fast-paths with 3-axis LLM rubric scoring.

Implements PRD Section 10:
1. Deterministic fast-path match against accepted reference answers (bypasses LLM in <5ms).
2. PydanticAI evaluation against 3 axes: grammatical_correctness, semantic_precision, pragmatic_appropriateness.
3. Strict gate evaluation: passed_gates is True iff grammatical >= 0.70 and semantic >= 0.70.
4. Specific taxonomy error tagging (ERR_QUESTION_MA, ERR_WORD_ORDER, ERR_MODAL_HUI, etc.).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from pydantic_ai import Agent

from goalcoach.domain.models import (
    AnswerSubmission,
    Exercise,
    GradingResult,
    RubricScores,
)
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    get_openrouter_model,
    run_with_fallback,
)

logger = logging.getLogger(__name__)

GRADER_SYSTEM_PROMPT = """You are the GoalCoach Chinese Grading Evaluator.
Assess the learner's Chinese submission against the exercise prompt and reference answers.

Evaluate along 3 distinct rubric axes (scores from 0.0 to 1.0):
1. `grammatical_correctness`: Word order, syntax, measure words, particle accuracy (吗, 呢, 了, 的).
2. `semantic_precision`: Accuracy of intended meaning and task fulfillment.
3. `pragmatic_appropriateness`: Register and conversational naturalness.

Gate Rule:
- `passed_gates` must be True if and only if:
  `grammatical_correctness >= 0.70` AND `semantic_precision >= 0.70`.

Error Taxonomy Codes:
If there is a mistake, tag specific codes in `detected_errors`, such as:
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
    system_prompt=GRADER_SYSTEM_PROMPT,
)


class GraderComponent:
    """Stateless evaluator producing rubric grading evidence for the Progress Service."""

    def __init__(self, agent: Agent = grader_agent) -> None:
        self.agent = agent

    async def grade(
        self,
        exercise: Exercise,
        answer: str | AnswerSubmission,
    ) -> GradingResult:
        """Evaluates submission against exercise rubrics with fast-path short-circuiting."""
        raw_answer = answer.answer if isinstance(answer, AnswerSubmission) else str(answer)
        clean_student_ans = raw_answer.strip()
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
            result, _ = await run_with_fallback(self.agent, prompt, deps=None)
            llm_result: GradingResult = result.output
            llm_result.exercise_id = exercise_id

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
            if has_critical_error:
                llm_result.passed_gates = False
            elif (
                llm_result.scores.grammatical_correctness < 0.70
                or llm_result.scores.semantic_precision < 0.70
            ):
                llm_result.passed_gates = False

            return llm_result
        except Exception as exc:
            logger.warning("GraderComponent LLM execution failed (%s); running heuristic evaluation.", exc)

        return self._heuristic_fallback(exercise, clean_student_ans, exercise_id)

    def _heuristic_fallback(
        self,
        exercise: Exercise,
        answer: str,
        exercise_id: Any,
    ) -> GradingResult:
        """Deterministic heuristic evaluator when offline or when LLM fails."""
        # Simple substring matching or particle checks
        passed = False
        detected_errors: list[str] = []
        feedback = "Good try, but please review the sentence structure."

        # Concept specific heuristic checks
        if "question_ma" in exercise.concept_id or "ma" in exercise.concept_id:
            if "吗" not in answer and "ma" not in answer.lower():
                detected_errors.append("ERR_QUESTION_MA")
                feedback = "Remember to add the question particle 吗 at the end of a yes/no question!"
            else:
                passed = True
                feedback = "Good job using the question particle 吗!"
        elif any(ref in answer for ref in exercise.reference_answers):
            passed = True
            feedback = "Well done! Your response conveys the intended meaning."
        elif len(answer) >= 2:
            # Partial credit
            passed = False
            detected_errors.append(f"ERR_{exercise.concept_id.upper()}")
            feedback = f"Check your grammar for concept {exercise.concept_id}."

        score = 0.85 if passed else 0.40
        return GradingResult(
            exercise_id=exercise_id,
            scores=RubricScores(
                grammatical_correctness=score,
                semantic_precision=score,
                pragmatic_appropriateness=score,
            ),
            passed_gates=passed,
            confidence=0.80,
            feedback=feedback,
            detected_errors=detected_errors,
            grader_version="deterministic-heuristic-fallback",
        )


__all__ = [
    "GRADER_SYSTEM_PROMPT",
    "GraderComponent",
    "grader_agent",
]
