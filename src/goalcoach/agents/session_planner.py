"""Adaptive Session Planner Component.

Plans an adaptive tree diagram (branching DAG) of exercises for an HSK concept session:
- If user answers correct: go left (advance difficulty / cognitive level).
- If user answers wrong: go right (remedial / scaffolding / contrast example).
- Structured Pydantic output with deterministic heuristic fallback when LLM is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from goalcoach.domain.models import LearnerState, SessionTree, SessionTreeNode
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    LLMUnavailableError,
    get_openrouter_model,
    get_output_retries,
    run_with_fallback,
)
from goalcoach.infrastructure.persistence.content_service import ContentService

logger = logging.getLogger(__name__)


@dataclass
class SessionPlannerDeps:
    """Dependencies for generating an adaptive session tree."""

    concept_id: str
    candidate_exercises: list[dict[str, Any]]
    state: LearnerState | None = None


SESSION_PLANNER_SYSTEM_PROMPT = """You are the Pedagogical Session Architect for GoalCoach.
Your mission is to construct an adaptive exercise tree diagram for a single Chinese HSK concept study session.

Core Architectural Rules:
1. STRICT GROUNDING: You MUST ONLY select `exercise_id` from the provided Candidate Exercises list. NEVER invent or hallucinate exercise IDs.
2. ADAPTIVE BRANCHING:
   - Left Branch (`on_correct`): Progress the learner forward. Increase difficulty (e.g. from recognition MCQ to association/fill-in-the-blank to production/sentence reorder).
   - Right Branch (`on_incorrect`): Offer pedagogical scaffolding. Provide an easier exercise, contrast exercise, or reinforcement exercise at the same or lower difficulty.
3. CONVERGENCE & TERMINATION:
   - The tree depth must be bounded (2 to 4 exercises along any single path).
   - Once a path reaches mastery or full remediation, set `on_correct: null` and/or `on_incorrect: null` and mark `is_terminal: true`.
   - Different branches may converge on the same consolidation node to ensure efficient exercise reuse.

Output Format:
Emit a valid `SessionTree` containing:
- `concept_id`: The target concept ID.
- `root_node_id`: The ID of the starting node (e.g. "root").
- `nodes`: A mapping of node_id -> SessionTreeNode.
- `rationale`: A 1-2 sentence explanation of the pedagogical design.
"""

session_planner_agent = Agent(
    model=get_openrouter_model(),
    deps_type=SessionPlannerDeps,
    output_type=SessionTree,
    output_retries=get_output_retries(),
    system_prompt=SESSION_PLANNER_SYSTEM_PROMPT,
)


def deterministic_build_session_tree(
    concept_id: str,
    exercises: list[Any],
    rationale: str = "Deterministic adaptive curriculum tree based on difficulty and exercise type.",
) -> SessionTree:
    """Construct a robust adaptive branching tree without an LLM."""
    if not exercises:
        raise LookupError(f"Cannot build session tree: No exercises found for concept {concept_id}")

    # Exercise taxonomy preference order
    type_priority = {
        "meaning_mcq": 1,
        "zh_to_en_mcq": 1,
        "en_to_zh_mcq": 2,
        "matching": 2,
        "dialogue_choice": 3,
        "fill_blank": 3,
        "reorder": 4,
        "translate_to_zh": 5,
    }

    # Sort exercises by difficulty, then canonical exercise order, then type priority
    sorted_ex = sorted(
        exercises,
        key=lambda e: (
            getattr(e, "difficulty", 1),
            getattr(e, "exercise_order", 0),
            type_priority.get(getattr(e, "exercise_type", ""), 3),
        ),
    )

    n = len(sorted_ex)
    nodes: dict[str, SessionTreeNode] = {}

    if n == 1:
        # Single exercise fallback
        ex = sorted_ex[0]
        nodes["root"] = SessionTreeNode(
            node_id="root",
            exercise_id=ex.exercise_id,
            exercise_type=getattr(ex, "exercise_type", "meaning_mcq"),
            difficulty=getattr(ex, "difficulty", 1),
            pedagogical_purpose="Single available concept practice",
            on_correct=None,
            on_incorrect=None,
            is_terminal=True,
        )
        return SessionTree(
            concept_id=concept_id,
            root_node_id="root",
            nodes=nodes,
            rationale=rationale,
            max_depth=1,
        )

    if n == 2:
        ex0, ex1 = sorted_ex[0], sorted_ex[1]
        nodes["root"] = SessionTreeNode(
            node_id="root",
            exercise_id=ex0.exercise_id,
            exercise_type=getattr(ex0, "exercise_type", "meaning_mcq"),
            difficulty=getattr(ex0, "difficulty", 1),
            pedagogical_purpose="Foundational recognition check",
            on_correct="node_challenge",
            on_incorrect="node_retry",
        )
        nodes["node_challenge"] = SessionTreeNode(
            node_id="node_challenge",
            exercise_id=ex1.exercise_id,
            exercise_type=getattr(ex1, "exercise_type", "fill_blank"),
            difficulty=getattr(ex1, "difficulty", 2),
            pedagogical_purpose="Higher difficulty application",
            on_correct=None,
            on_incorrect=None,
            is_terminal=True,
        )
        nodes["node_retry"] = SessionTreeNode(
            node_id="node_retry",
            exercise_id=ex0.exercise_id,
            exercise_type=getattr(ex0, "exercise_type", "meaning_mcq"),
            difficulty=getattr(ex0, "difficulty", 1),
            pedagogical_purpose="Scaffolded reinforcement retry",
            on_correct="node_challenge",
            on_incorrect=None,
            is_terminal=False,
        )
        return SessionTree(
            concept_id=concept_id,
            root_node_id="root",
            nodes=nodes,
            rationale=rationale,
            max_depth=2,
        )

    # 3 or more exercises: construct 3-tier adaptive diamond tree
    # root (recognition)
    # ├── on_correct (left) -> pass_step (association/application)
    # │    ├── on_correct (left) -> challenge_step (production) -> Complete
    # │    └── on_incorrect (right) -> support_step -> Complete
    # └── on_incorrect (right) -> remedial_step (reinforcement)
    #      ├── on_correct (left) -> pass_step
    #      └── on_incorrect (right) -> support_step -> Exit
    root_ex = sorted_ex[0]
    pass_ex = sorted_ex[1]
    challenge_ex = sorted_ex[min(2, n - 1)]
    remedial_ex = sorted_ex[0]  # retry or simplest
    support_ex = sorted_ex[min(1, n - 1)]

    # If we have 4+ exercises, use distinct exercises for support/remedial
    if n >= 4:
        challenge_ex = sorted_ex[-1]
        remedial_ex = sorted_ex[2]
        support_ex = sorted_ex[1]

    nodes["root"] = SessionTreeNode(
        node_id="root",
        exercise_id=root_ex.exercise_id,
        exercise_type=getattr(root_ex, "exercise_type", "meaning_mcq"),
        difficulty=getattr(root_ex, "difficulty", 1),
        pedagogical_purpose="Core concept comprehension check",
        on_correct="step_pass",
        on_incorrect="step_remedial",
    )
    nodes["step_pass"] = SessionTreeNode(
        node_id="step_pass",
        exercise_id=pass_ex.exercise_id,
        exercise_type=getattr(pass_ex, "exercise_type", "fill_blank"),
        difficulty=getattr(pass_ex, "difficulty", 1),
        pedagogical_purpose="Pattern association and usage",
        on_correct="step_challenge",
        on_incorrect="step_support",
    )
    nodes["step_remedial"] = SessionTreeNode(
        node_id="step_remedial",
        exercise_id=remedial_ex.exercise_id,
        exercise_type=getattr(remedial_ex, "exercise_type", "meaning_mcq"),
        difficulty=getattr(remedial_ex, "difficulty", 1),
        pedagogical_purpose="Scaffolded alternative check after initial mistake",
        on_correct="step_pass",
        on_incorrect="step_support",
    )
    nodes["step_challenge"] = SessionTreeNode(
        node_id="step_challenge",
        exercise_id=challenge_ex.exercise_id,
        exercise_type=getattr(challenge_ex, "exercise_type", "reorder"),
        difficulty=getattr(challenge_ex, "difficulty", 2),
        pedagogical_purpose="Target mastery and production challenge",
        on_correct=None,
        on_incorrect=None,
        is_terminal=True,
    )
    nodes["step_support"] = SessionTreeNode(
        node_id="step_support",
        exercise_id=support_ex.exercise_id,
        exercise_type=getattr(support_ex, "exercise_type", "fill_blank"),
        difficulty=getattr(support_ex, "difficulty", 1),
        pedagogical_purpose="Consolidation practice before concluding session",
        on_correct=None,
        on_incorrect=None,
        is_terminal=True,
    )

    return SessionTree(
        concept_id=concept_id,
        root_node_id="root",
        nodes=nodes,
        rationale=rationale,
        max_depth=3,
    )


class SessionPlanner:
    """Coordinates session tree planning with strict curriculum grounding and fallback."""

    def __init__(self, agent: Agent = session_planner_agent) -> None:
        self.agent = agent

    async def plan_session_tree(
        self,
        concept_id: str,
        content_service: ContentService,
        state: LearnerState | None = None,
    ) -> SessionTree:
        """Generate an adaptive session tree using LLM with deterministic fallback."""
        all_exercises = content_service.get_exercises_for_concept(concept_id, limit=10)
        if not all_exercises:
            raise LookupError(f"No exercises available for concept {concept_id}")

        candidates_data = [
            {
                "exercise_id": e.exercise_id,
                "exercise_type": getattr(e, "exercise_type", "unknown"),
                "difficulty": getattr(e, "difficulty", 1),
                "instruction": e.instruction or "",
                "prompt": e.prompt,
            }
            for e in all_exercises
        ]
        valid_ids = {e.exercise_id for e in all_exercises}

        deps = SessionPlannerDeps(
            concept_id=concept_id,
            candidate_exercises=candidates_data,
            state=state,
        )

        prompt = (
            f"Target Concept ID: {concept_id}\n"
            f"Learner Goal: {state.goal.title if state and state.goal else 'HSK 1 Chinese'}\n"
            f"Candidate Exercises Available (SELECT ONLY FROM THESE):\n"
            + "\n".join(
                f"- ID: {c['exercise_id']} | Type: {c['exercise_type']} | Difficulty: {c['difficulty']} | Prompt: {c['prompt']}"
                for c in candidates_data
            )
            + "\n\nPlan the optimal adaptive exercise tree diagram. Connect nodes via on_correct (left, advance) and on_incorrect (right, reinforce)."
        )

        try:
            result, provider = await run_with_fallback(
                self.agent,
                prompt,
                deps=deps,
                component="session_planner",
            )
            tree: SessionTree = result.output

            # Sanity check: Ensure all exercise_ids are grounded in Database #1
            # and root_node_id exists in nodes
            if tree.root_node_id in tree.nodes:
                all_grounded = all(node.exercise_id in valid_ids for node in tree.nodes.values())
                if all_grounded:
                    logger.info("Session planner successfully generated grounded tree via %s", provider)
                    return tree
                logger.warning("Session planner generated ungrounded exercise IDs; falling back.")
            else:
                logger.warning("Session planner root_node_id not found in nodes; falling back.")
        except LLMUnavailableError as exc:
            logger.info("LLM unavailable for session planner (%s); using deterministic tree.", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Session planner failed (%s); using deterministic tree.", exc)

        return deterministic_build_session_tree(concept_id, all_exercises)
