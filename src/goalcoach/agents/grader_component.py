"""Grader Component: Stateless evaluator combining deterministic fast-paths with 3-axis LLM rubric scoring.

Implements PRD Section 10:
1. Deterministic fast-path match against accepted reference answers (bypasses LLM in <5ms).
2. PydanticAI evaluation against 3 axes: grammatical_correctness, semantic_precision, pragmatic_appropriateness.
3. Strict gate evaluation: passed_gates is True iff grammatical >= 0.70 and semantic >= 0.70.
4. Specific taxonomy error tagging (ERR_QUESTION_MA, ERR_WORD_ORDER, ERR_MODAL_HUI, etc.).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

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


def parse_matching_pairs(text: str) -> dict[str, str]:
    """Parse various matching input formats into a normalized dict of {left_id: right_id}."""
    text = text.strip()
    if not text:
        return {}

    # 1. JSON parsing
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if "pairs" in data and isinstance(data["pairs"], dict):
                return {str(k).upper(): str(v).upper() for k, v in data["pairs"].items()}
            return {str(k).upper(): str(v).upper() for k, v in data.items()}
        except (json.JSONDecodeError, TypeError, KeyError, AttributeError):
            logger.debug("Failed to parse text as JSON matching pairs: %s", text)

    # 2. Key-value matching like "1C 2A 3D 4B 5E", "1-C, 2-A", "1:C 2:A"
    pair_matches = re.findall(r"(\d+)\s*[-:=]?\s*([A-Za-z]+)", text)
    if pair_matches:
        return {num: letter.upper() for num, letter in pair_matches}

    # 3. Comma/space separated letters: "C, A, D, B, E" or "C A D B E"
    tokens = [t.strip().upper() for t in re.split(r"[\s,;]+", text) if t.strip()]
    if tokens and all(len(t) == 1 and t.isalpha() for t in tokens):
        return {str(i + 1): token for i, token in enumerate(tokens)}

    return {}


class GraderComponent:
    """Stateless evaluator producing rubric grading evidence for the Progress Service."""

    def __init__(self, agent: Agent = grader_agent) -> None:
        self.agent = agent

    @staticmethod
    def _grade_matching_exercise(
        exercise: Exercise,
        student_answer: str,
        exercise_id: Any,
    ) -> GradingResult:
        """Deterministically evaluates mix-and-match pairs in <1ms."""
        expected_pairs: dict[str, str] = {}
        for ref in exercise.reference_answers:
            parsed = parse_matching_pairs(ref)
            if parsed:
                expected_pairs = parsed
                break

        if (
            not expected_pairs
            and isinstance(exercise.metadata, dict)
            and "pairs" in exercise.metadata
        ):
            expected_pairs = {
                str(k).upper(): str(v).upper() for k, v in exercise.metadata["pairs"].items()
            }

        student_pairs = parse_matching_pairs(student_answer)
        if not student_pairs:
            return GradingResult(
                exercise_id=exercise_id,
                scores=RubricScores(
                    grammatical_correctness=0.0,
                    semantic_precision=0.0,
                    pragmatic_appropriateness=0.5,
                ),
                passed_gates=False,
                confidence=1.0,
                feedback="Please format your answer matching numbers to letters (e.g., 1C 2A 3E 4B 5D).",
                detected_errors=["ERR_FORMAT_MATCHING"],
                grader_version="deterministic-matching",
            )

        total_pairs = len(expected_pairs) or max(len(student_pairs), 1)
        matched_correct = 0

        for left_key, right_val in expected_pairs.items():
            if student_pairs.get(left_key) == right_val:
                matched_correct += 1

        precision = matched_correct / max(1, total_pairs)
        passed = precision >= 0.80  # 4 out of 5 passes

        if passed:
            feedback = (
                f"Outstanding! All {matched_correct}/{total_pairs} pairs matched perfectly!"
                if matched_correct == total_pairs
                else f"Great job! You matched {matched_correct}/{total_pairs} pairs correctly."
            )
            errors = []
        else:
            feedback = (
                f"Good attempt! You matched {matched_correct}/{total_pairs} pairs correctly. "
                "Review the remaining vocabulary pairs."
            )
            errors = ["ERR_VOCAB_MATCH"]

        return GradingResult(
            exercise_id=exercise_id,
            scores=RubricScores(
                grammatical_correctness=1.0,
                semantic_precision=precision,
                pragmatic_appropriateness=1.0,
            ),
            passed_gates=passed,
            confidence=1.0,
            feedback=feedback,
            detected_errors=errors,
            grader_version="deterministic-matching",
        )

    async def grade(
        self,
        exercise: Exercise,
        answer: str,
    ) -> GradingResult:
        """Evaluates submission against exercise rubrics with fast-path short-circuiting."""
        clean_student_ans = answer.strip()
        exercise_id = exercise.id or uuid4()

        # Check for matching exercise evaluation (deterministic <1ms fast path)
        if getattr(exercise, "exercise_type", "") == "matching" or (
            isinstance(exercise.options, dict)
            and "left" in exercise.options
            and "right" in exercise.options
        ):
            return self._grade_matching_exercise(exercise, clean_student_ans, exercise_id)

        # 1. Fast Path: Exact reference answer match (bypasses LLM, <5ms)
        accepted = [ans.strip() for ans in exercise.reference_answers if ans]

        # If exercise has options (MCQ), check if user selected by index or letter (e.g. 1, 2, A, B)
        resolved_answer = clean_student_ans
        if exercise.options and isinstance(exercise.options, list) and len(exercise.options) > 0:
            if clean_student_ans.isdigit():
                idx = int(clean_student_ans) - 1
                if 0 <= idx < len(exercise.options):
                    resolved_answer = exercise.options[idx].strip()
            elif clean_student_ans.upper() in ("A", "B", "C", "D"):
                idx = ord(clean_student_ans.upper()) - ord("A")
                if 0 <= idx < len(exercise.options):
                    resolved_answer = exercise.options[idx].strip()

        if clean_student_ans in accepted or resolved_answer in accepted:
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
            result, provider = await run_with_fallback(
                self.agent,
                prompt,
                deps=None,
                component="grader_component",
            )
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
