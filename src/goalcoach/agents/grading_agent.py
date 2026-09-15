"""
src/goalcoach/agents/grading_agent.py
Rubric-based evaluation agent for Chinese sentence submissions implemented with PydanticAI.
"""

from __future__ import annotations

from pydantic_ai import Agent

from goalcoach.agents.interfaces import GradingOutcome
from goalcoach.domain.models import AnswerSubmission, Exercise, GradingResult, RubricScores
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    get_openrouter_model,
    run_with_fallback,
)

_grading_evaluator = Agent(
    model=get_openrouter_model(),
    output_type=GradingResult,
    system_prompt=(
        "You are the GoalCoach Chinese Grading Evaluator. "
        "Grade the student's Chinese sentence against 3 dimensions: "
        "1. grammatical_correctness, 2. semantic_precision, 3. pragmatic_appropriateness. "
        "Each score must be between 0.0 and 1.0. "
        "Gate rule: passed_gates is true only if grammatical_correctness >= 0.70 "
        "and semantic_precision >= 0.70."
    ),
)


class PydanticAIGrader:
    """Passive structured grader with deterministic and LLM-backed paths."""

    async def grade(
        self,
        exercise: Exercise,
        submission: AnswerSubmission,
    ) -> GradingOutcome:
        """Evaluate one answer without choosing the next teaching action."""
        normalized_answer = submission.answer.strip()
        normalized_references = {
            reference.strip() for reference in exercise.reference_answers
        }

        if normalized_answer in normalized_references:
            result = GradingResult(
                exercise_id=exercise.id,
                scores=RubricScores(
                    grammatical_correctness=1.0,
                    semantic_precision=1.0,
                    pragmatic_appropriateness=1.0,
                ),
                passed_gates=True,
                confidence=1.0,
                feedback="Perfect! Your answer matches the accepted standard response.",
                grader_version="deterministic-fast-path",
            )
            return GradingOutcome(
                result=result,
                provider="deterministic:rule_match",
            )

        prompt = (
            f"Exercise Prompt: {exercise.prompt}\n"
            f"Target Concept: {exercise.concept_id}\n"
            f"Target Instruction: {exercise.target_instruction}\n"
            f"Student Answer: {submission.answer}\n"
            f"Reference Answers: {', '.join(exercise.reference_answers)}"
        )
        run_result, provider = await run_with_fallback(
            _grading_evaluator,
            prompt,
            deps=None,
        )
        return GradingOutcome(result=run_result.output, provider=provider)


_default_grader = PydanticAIGrader()


async def grade_submission(
    exercise: Exercise,
    submission: AnswerSubmission,
) -> tuple[GradingResult, str]:
    """Compatibility facade retained for API and integration callers."""
    outcome = await _default_grader.grade(exercise, submission)
    return outcome.result, outcome.provider
