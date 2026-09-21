"""Planning Agent implemented with PydanticAI.

Answers: 'Given the current learner state and curriculum graph, what should the student do next?'
Produces a validated PlanUpdate schema strictly bounded by the learner's time budget and prerequisites.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext

from goalcoach.application.agent_history import format_agent_history
from goalcoach.domain.enums import PlanItemKind
from goalcoach.domain.models import LearnerState, PlanItem, PlanUpdate
from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.llm.pydantic_ai_models import (
    AgentOutputError,
    LLMUnavailableError,
    get_openrouter_model,
    get_output_retries,
    run_with_fallback,
)
from goalcoach.infrastructure.persistence.content_service import ContentService


def validate_agent_roadmap(
    proposed_ids: list[str],
    curriculum_ids: list[str],
) -> list[str]:
    """Keep only the unique, curriculum-valid concepts selected by the agent."""
    valid_ids = set(curriculum_ids)
    return list(dict.fromkeys(cid for cid in proposed_ids if cid in valid_ids))


@dataclass
class PlanningDeps:
    """Dependencies injected into the Planning Agent."""

    state: LearnerState
    content_service: ContentService
    enable_prerequisites: bool


PLANNING_SYSTEM_PROMPT = """You are the GoalCoach Adaptive Curriculum Planner for HSK1 Chinese.
Your responsibility is to decide what the learner should study next based on their goal, time budget, mastery history, and prerequisite graph.

Key Pedagogical Rules:
1. Prioritize Review & Remediation:
   - If `needs_replanning` is True or recurring error tags exist, prioritize REMEDIAL items for the weak concepts and postpone introducing new topics.
   - Schedule REVIEW items for concepts due for spaced review or with low retention.
2. Introduce Feasible New Topics:
   - Schedule NEW concepts only if their prerequisites are satisfied. A prerequisite is satisfied if the learner has mastery >= 0.50 OR completed remediation today.
   - If a concept has already been studied or remediated today (listed in Remediated Today / Studied Today), do not schedule it again today; advance to subsequent concepts.
3. Strict Budget Allocation:
   - The sum of `estimated_minutes` across `ordered_items` must not exceed `daily_allocation_minutes`.
   - Categorize each item kind strictly as 'review', 'remedial', or 'new'.
4. Curriculum Fidelity:
   - Only output valid concept_id strings provided by the curriculum tool.
5. Adaptation Rationale:
   - Provide a clear, transparent explanation in `adaptation_rationale` explaining why this plan was chosen.
6. Dynamic Roadmap:
   - Produce a non-empty `roadmap_concept_ids` subset containing only concepts relevant to the
     learner's free-form goal, evidence, and errors. Do not include the full catalog by default.
   - Order the selected concepts by relevance and learning sequence.
   - Reason directly from the goal and each concept's communicative purpose; do not use fixed goal categories.
   - Keep prerequisites before concepts that depend on them.
7. Cross-Session Continuity:
   - Use the compact learning history as evidence when choosing review, remediation, and new work.
   - Avoid needless immediate repetition, but repeat a concept when its outcome or error evidence justifies it.
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
            "communicative_goal": c.communicative_goal,
            "grammar_focus": c.grammar_focus,
            "vocabulary_focus": c.vocabulary_focus,
            "metadata": c.metadata_json or {},
            "prerequisites": ctx.deps.content_service.get_prerequisites(c.concept_id),
        }
        for c in concepts
    ]


@planning_agent.tool
def get_concept_prerequisites(ctx: RunContext[PlanningDeps], concept_id: str) -> list[str]:
    """Fetch prerequisite concept IDs that must be mastered before studying this concept."""
    if not ctx.deps.enable_prerequisites:
        return []
    return ctx.deps.content_service.get_prerequisites(concept_id)


class PlanningWorker:
    """Wrapper class managing the execution, validation, and deterministic fallback for planning."""

    def __init__(
        self,
        agent: Agent = planning_agent,
        *,
        enable_prerequisites: bool | None = None,
    ) -> None:
        self.agent = agent
        self.enable_prerequisites = (
            Settings().enable_prerequisites
            if enable_prerequisites is None
            else enable_prerequisites
        )

    async def create_plan(
        self,
        state: LearnerState,
        content_service: ContentService,
    ) -> PlanUpdate:
        """Invokes the Planning Agent with fallback to deterministic heuristic rules."""
        deps = PlanningDeps(
            state=state,
            content_service=content_service,
            enable_prerequisites=self.enable_prerequisites,
        )
        available_minutes = (
            state.active_session.planned_minutes
            if state.active_session is not None
            else (state.goal.daily_available_minutes if state.goal else 20)
        )

        # Construct concise prompt summarizing learner context
        mastery_summary = {
            cid: {
                "score": round(m.mastery_score, 2),
                "retention": round(m.current_retention(), 2),
                "is_due": m.is_review_due(),
            }
            for cid, m in state.mastery.items()
        }
        error_summary = [
            {"code": err.code, "concept_id": err.concept_id, "occurrences": err.occurrences}
            for err in state.error_profile
        ]

        remediated_summary = ", ".join(state.today_remediated_concept_ids) or "None"
        studied_summary = ", ".join(state.today_studied_concept_ids) or "None"
        history_summary = format_agent_history(state)

        prompt = (
            f"Learner Goal: {state.goal.title if state.goal else 'HSK1'}\n"
            f"Daily Time Budget: {available_minutes} minutes\n"
            f"Needs Replanning: {state.needs_replanning}\n"
            f"Prerequisite Enforcement Enabled: {self.enable_prerequisites}\n"
            f"Remediated Today: {remediated_summary}\n"
            f"Studied Today: {studied_summary}\n"
            f"Current Mastery: {mastery_summary}\n"
            f"Active Errors: {error_summary}\n"
            f"Recent Cross-Session Learning History:\n{history_summary}\n"
            "Generate today's optimal PlanUpdate and a complete personalized roadmap "
            "conforming to the schema."
        )

        try:
            result, provider = await run_with_fallback(self.agent, prompt, deps=deps)
            plan_update: PlanUpdate = result.output
            plan_update.metadata.update(
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

            # Guardrail: Validate all concept IDs against Database #1
            curriculum_ids = [c.concept_id for c in content_service.list_all_concepts()]
            all_valid_ids = set(curriculum_ids)
            plan_update.roadmap_concept_ids = validate_agent_roadmap(
                plan_update.roadmap_concept_ids,
                curriculum_ids,
            )
            validated_items = [
                item for item in plan_update.ordered_items if item.concept_id in all_valid_ids
            ]
            daily_ids = list(dict.fromkeys(item.concept_id for item in validated_items))
            plan_update.roadmap_concept_ids = list(
                dict.fromkeys([*plan_update.roadmap_concept_ids, *daily_ids])
            )

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
                    # Guardrail: Validate DAG prerequisites for scheduled NEW concepts
                    prereq_graph = (
                        content_service.get_all_prerequisites()
                        if self.enable_prerequisites
                        else {}
                    )
                    validated_budgeted: list[PlanItem] = []
                    for item in budgeted_items:
                        if item.kind == PlanItemKind.NEW:
                            if (
                                item.concept_id in state.today_remediated_concept_ids
                                or item.concept_id in state.today_studied_concept_ids
                            ):
                                continue
                            prereqs = prereq_graph.get(item.concept_id, frozenset())
                            prereqs_met = all(
                                (
                                    p in state.mastery
                                    and (
                                        state.mastery[p].mastery_score >= 0.50
                                        or p in state.today_remediated_concept_ids
                                    )
                                )
                                for p in prereqs
                            )
                            if not prereqs_met:
                                continue
                        validated_budgeted.append(item)

                    if validated_budgeted:
                        plan_update.ordered_items = validated_budgeted
                        plan_update.daily_allocation_minutes = sum(
                            it.estimated_minutes for it in validated_budgeted
                        )
                        return plan_update

        except LLMUnavailableError as exc:
            return self._deterministic_fallback(
                state,
                content_service,
                available_minutes,
                notice=f"LLM unavailable; deterministic planning fallback used: {exc}",
            )
        return self._deterministic_fallback(
            state,
            content_service,
            available_minutes,
            notice="Planning Agent returned no valid items; deterministic fallback used.",
        )

    def _deterministic_fallback(
        self,
        state: LearnerState,
        content_service: ContentService,
        available_minutes: int,
        *,
        notice: str,
    ) -> PlanUpdate:
        """Create a conservative, curriculum-grounded plan when model reasoning is unavailable."""
        concepts = content_service.list_all_concepts()
        if not concepts:
            raise AgentOutputError("No curriculum concepts are available for deterministic planning")
        concept_by_id = {concept.concept_id: concept for concept in concepts}
        catalog_ids = [concept.concept_id for concept in concepts]
        prerequisite_graph = (
            content_service.get_all_prerequisites() if self.enable_prerequisites else {}
        )
        selected: list[PlanItem] = []
        allocated = 0

        weak_ids = list(
            dict.fromkeys(
                error.concept_id
                for error in sorted(
                    state.error_profile,
                    key=lambda item: item.occurrences,
                    reverse=True,
                )
                if error.concept_id in concept_by_id
                and error.concept_id not in state.today_remediated_concept_ids
            )
        )
        due_ids = [
            concept_id
            for concept_id, mastery in state.mastery.items()
            if concept_id in concept_by_id and mastery.is_review_due()
        ]
        new_ids = [
            concept_id
            for concept_id in catalog_ids
            if concept_id not in state.mastery
            and concept_id not in state.today_studied_concept_ids
        ]

        candidates = [
            *((concept_id, PlanItemKind.REMEDIAL, 10) for concept_id in weak_ids),
            *((concept_id, PlanItemKind.REVIEW, 5) for concept_id in due_ids),
            *((concept_id, PlanItemKind.NEW, 5) for concept_id in new_ids),
        ]
        for concept_id, kind, requested_minutes in candidates:
            if concept_id in {item.concept_id for item in selected}:
                continue
            prerequisites = prerequisite_graph.get(concept_id, frozenset())
            prerequisites_met = all(
                prerequisite_id in state.mastery
                and (
                    state.mastery[prerequisite_id].mastery_score >= 0.5
                    or prerequisite_id in state.today_remediated_concept_ids
                )
                for prerequisite_id in prerequisites
            )
            if kind == PlanItemKind.NEW and not prerequisites_met:
                continue
            remaining = available_minutes - allocated
            if remaining <= 0:
                break
            minutes = min(requested_minutes, remaining)
            concept = concept_by_id[concept_id]
            selected.append(
                PlanItem(
                    concept_id=concept_id,
                    kind=kind,
                    objective=f"{concept.title_en}: {concept.communicative_goal}",
                    estimated_minutes=minutes,
                )
            )
            allocated += minutes

        if not selected:
            concept = concepts[0]
            minutes = min(5, available_minutes)
            selected.append(
                PlanItem(
                    concept_id=concept.concept_id,
                    kind=PlanItemKind.NEW,
                    objective=f"{concept.title_en}: {concept.communicative_goal}",
                    estimated_minutes=minutes,
                )
            )
            allocated = minutes

        return PlanUpdate(
            daily_allocation_minutes=allocated,
            ordered_items=selected,
            adaptation_rationale="Deterministic curriculum and learner-state allocation.",
            roadmap_adjustments=["Deterministic fallback retained the canonical roadmap."],
            roadmap_concept_ids=list(
                dict.fromkeys(
                    [*state.roadmap_concept_ids, *(item.concept_id for item in selected)]
                )
            ),
            metadata={
                "provider": "deterministic",
                "fallback_used": True,
                "notice": notice,
            },
        )

__all__ = [
    "PLANNING_SYSTEM_PROMPT",
    "PlanningDeps",
    "PlanningWorker",
    "planning_agent",
    "validate_agent_roadmap",
]
