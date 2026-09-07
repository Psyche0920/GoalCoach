"""
src/goalcoach/agents/grading_agent.py
Rubric-based evaluation agent for Chinese sentence submissions implemented with PydanticAI.
"""

from __future__ import annotations

from pydantic_ai import Agent

from goalcoach.domain.models import AnswerSubmission, Exercise, GradingResult, RubricScores
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    get_openrouter_model,
    run_with_fallback,
)

grader_agent = Agent(
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


async def grade_submission(
    exercise: Exercise, submission: AnswerSubmission
) -> tuple[GradingResult, str]:
    """Evaluates a learner's submission against exercise rubrics with fast-path short-circuiting."""
    # Fast path: deterministic match on reference answers
    if submission.answer.strip() in [ans.strip() for ans in exercise.reference_answers]:
        return (
            GradingResult(
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
            ),
            "deterministic:rule_match",
        )

    # LLM grading path
    prompt = (
        f"Exercise Prompt: {exercise.prompt}\n"
        f"Target Concept: {exercise.concept_id}\n"
        f"Target Instruction: {exercise.target_instruction}\n"
        f"Student Answer: {submission.answer}\n"
        f"Reference Answers: {', '.join(exercise.reference_answers)}"
    )
    result, provider = await run_with_fallback(grader_agent, prompt, deps=None)
    return result.output, provider
