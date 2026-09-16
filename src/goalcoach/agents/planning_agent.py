"""Planning Agent implemented with PydanticAI.

Answers: 'Given the current learner state and curriculum graph, what should the student do next?'
Produces a validated PlanUpdate schema strictly bounded by the learner's time budget and prerequisites.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext

from goalcoach.domain.enums import PlanItemKind
from goalcoach.domain.models import LearnerState, PlanItem, PlanUpdate
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    get_openrouter_model,
    get_output_retries,
    run_with_fallback,
)
from goalcoach.infrastructure.persistence.content_service import ContentService

logger = logging.getLogger(__name__)


@dataclass
class PlanningDeps:
    """Dependencies injected into the Planning Agent."""

    state: LearnerState
    content_service: ContentService


PLANNING_SYSTEM_PROMPT = """You are the GoalCoach Adaptive Curriculum Planner for HSK1 Chinese.
Your responsibility is to decide what the learner should study next based on their goal, time budget, mastery history, and prerequisite graph.

Key Pedagogical Rules:
1. Prioritize Review & Remediation:
   - If `needs_replanning` is True or recurring error tags exist, prioritize REMEDIAL items for the weak concepts and postpone introducing new topics.
   - Schedule REVIEW items for concepts due for spaced review or with low retention.
2. Introduce Feasible New Topics:
   - Schedule NEW concepts only if their prerequisites are satisfied.
3. Strict Budget Allocation:
   - The sum of `estimated_minutes` across `ordered_items` must not exceed `daily_allocation_minutes`.
   - Categorize each item kind strictly as 'review', 'remedial', or 'new'.
4. Curriculum Fidelity:
   - Only output valid concept_id strings provided by the curriculum tool.
5. Adaptation Rationale:
   - Provide a clear, transparent explanation in `adaptation_rationale` explaining why this plan was chosen.
"""

planning_agent = Agent(
    model=get_openrouter_model(),
    deps_type=PlanningDeps,
    output_type=PlanUpdate,
    output_retries=get_output_retries(),
    system_prompt=PLANNING_SYSTEM_PROMPT,
)


@planning_agent.tool
def get_curriculum_catalog(ctx: RunContext[PlanningDeps]) -> list[dict[str, Any]]:
    """List available HSK1 curriculum concepts with difficulty and sequencing."""
    concepts = ctx.deps.content_service.list_all_concepts(hsk_level=1)
    return [
        {
            "concept_id": c.concept_id,
            "title_zh": c.title_zh,
            "title_en": c.title_en,
            "sequence_no": c.sequence_no,
            "difficulty": c.difficulty,
        }
        for c in concepts
    ]


@planning_agent.tool
def get_concept_prerequisites(ctx: RunContext[PlanningDeps], concept_id: str) -> list[str]:
    """Fetch prerequisite concept IDs that must be mastered before studying this concept."""
    return ctx.deps.content_service.get_prerequisites(concept_id)


class PlanningWorker:
    """Wrapper class managing the execution, validation, and deterministic fallback for planning."""

    def __init__(self, agent: Agent = planning_agent) -> None:
        self.agent = agent

    async def create_plan(
        self,
        state: LearnerState,
        content_service: ContentService,
    ) -> PlanUpdate:
        """Invokes the Planning Agent with fallback to deterministic heuristic rules."""
        deps = PlanningDeps(state=state, content_service=content_service)
        available_minutes = state.goal.daily_available_minutes if state.goal else 20

        # Construct concise prompt summarizing learner context
        mastery_summary = {
            cid: {
                "score": round(m.mastery_score, 2),
                "retention": round(m.retention_score, 2),
                "is_due": m.is_review_due(),
            }
            for cid, m in state.mastery.items()
        }
        error_summary = [
            {"code": err.code, "concept_id": err.concept_id, "occurrences": err.occurrences}
            for err in state.error_profile
        ]

        prompt = (
            f"Learner Goal: {state.goal.title if state.goal else 'HSK1'}\n"
            f"Daily Time Budget: {available_minutes} minutes\n"
            f"Needs Replanning: {state.needs_replanning}\n"
            f"Interests: {state.context_interests}\n"
            f"Current Mastery: {mastery_summary}\n"
            f"Active Errors: {error_summary}\n"
            "Generate today's optimal PlanUpdate conforming to the schema."
        )

        try:
            result, _ = await run_with_fallback(self.agent, prompt, deps=deps)
            plan_update: PlanUpdate = result.output

            # Guardrail: Validate all concept IDs against Database #1
            all_valid_ids = {c.concept_id for c in content_service.list_all_concepts()}
            validated_items = [
                item for item in plan_update.ordered_items if item.concept_id in all_valid_ids
            ]

            if validated_items:
                # Ensure budget not exceeded
                running_sum = 0
                budgeted_items: list[PlanItem] = []
                for item in validated_items:
                    if running_sum + item.estimated_minutes <= available_minutes:
                        budgeted_items.append(item)
                        running_sum += item.estimated_minutes
                    elif running_sum < available_minutes:
                        remaining = available_minutes - running_sum
                        item.estimated_minutes = remaining
                        budgeted_items.append(item)
                        break

                if budgeted_items:
                    plan_update.ordered_items = budgeted_items
                    plan_update.daily_allocation_minutes = sum(it.estimated_minutes for it in budgeted_items)
                    return plan_update

        except Exception as exc:
            logger.warning("PlanningAgent LLM execution failed (%s); using deterministic heuristic.", exc)

        # Deterministic Heuristic Fallback
        return self._heuristic_fallback(state, content_service, available_minutes)

    def _heuristic_fallback(
        self,
        state: LearnerState,
        content_service: ContentService,
        available_minutes: int,
    ) -> PlanUpdate:
        """Deterministic algorithm guaranteeing valid PlanUpdate execution."""
        all_concepts = content_service.list_all_concepts()
        all_ids = [c.concept_id for c in all_concepts] or ["hsk1_c01", "hsk1_c02"]
        prereq_graph = content_service.get_all_prerequisites()

        items: list[PlanItem] = []
        allocated_minutes = 0

        # 1. Remedial: Check errors or weak mastery (< 0.60)
        remedial_candidates: list[str] = []
        if state.needs_replanning and state.error_profile:
            # Prioritize concept with most frequent error
            sorted_errors = sorted(state.error_profile, key=lambda e: e.occurrences, reverse=True)
            remedial_candidates.extend(e.concept_id for e in sorted_errors)

        for cid, m in state.mastery.items():
            if m.mastery_score < 0.60 and cid not in remedial_candidates:
                remedial_candidates.append(cid)

        for cid in remedial_candidates:
            if allocated_minutes + 10 <= available_minutes:
                items.append(
                    PlanItem(
                        concept_id=cid,
                        kind=PlanItemKind.REMEDIAL,
                        objective=f"Strengthen weak concept {cid} through targeted practice",
                        estimated_minutes=10,
                    )
                )
                allocated_minutes += 10
            if allocated_minutes >= available_minutes:
                break

        # 2. Spaced Review
        for cid, m in state.mastery.items():
            if m.is_review_due() and cid not in [it.concept_id for it in items]:
                if allocated_minutes + 5 <= available_minutes:
                    items.append(
                        PlanItem(
                            concept_id=cid,
                            kind=PlanItemKind.REVIEW,
                            objective=f"Review spaced repetition concept {cid}",
                            estimated_minutes=5,
                        )
                    )
                    allocated_minutes += 5
            if allocated_minutes >= available_minutes:
                break

        # 3. New Concepts (only if needs_replanning is False or budget allows)
        if not state.needs_replanning or not items:
            for cid in all_ids:
                if cid not in state.mastery and cid not in [it.concept_id for it in items]:
                    # Check prerequisites
                    prereqs = prereq_graph.get(cid, frozenset())
                    prereqs_met = all(
                        (p in state.mastery and state.mastery[p].mastery_score >= 0.50)
                        for p in prereqs
                    )
                    if prereqs_met:
                        if allocated_minutes + 5 <= available_minutes:
                            items.append(
                                PlanItem(
                                    concept_id=cid,
                                    kind=PlanItemKind.NEW,
                                    objective=f"Master new concept {cid}",
                                    estimated_minutes=5,
                                )
                            )
                            allocated_minutes += 5
                if allocated_minutes >= available_minutes or len(items) >= 4:
                    break

        # If nothing allocated, add first curriculum concept
        if not items:
            default_id = all_ids[0]
            items.append(
                PlanItem(
                    concept_id=default_id,
                    kind=PlanItemKind.NEW,
                    objective=f"Introduction to HSK1: {default_id}",
                    estimated_minutes=min(10, available_minutes),
                )
            )
            allocated_minutes = items[0].estimated_minutes

        rationale = (
            f"Adaptive plan created ({allocated_minutes}m allocated): "
            f"{sum(1 for i in items if i.kind == PlanItemKind.REMEDIAL)} remedial, "
            f"{sum(1 for i in items if i.kind == PlanItemKind.REVIEW)} review, "
            f"{sum(1 for i in items if i.kind == PlanItemKind.NEW)} new."
        )
        if state.needs_replanning:
            rationale += " Adjusted to prioritize remediation after detected recurring errors."

        return PlanUpdate(
            daily_allocation_minutes=allocated_minutes,
            ordered_items=items,
            adaptation_rationale=rationale,
            roadmap_adjustments=["Remediate error concepts first"] if state.needs_replanning else [],
        )


__all__ = [
    "PLANNING_SYSTEM_PROMPT",
    "PlanningDeps",
    "PlanningWorker",
    "planning_agent",
]
