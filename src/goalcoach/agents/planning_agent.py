"""Planning Agent implemented with PydanticAI.

Answers: 'Given the current learner state and curriculum graph, what should the student do next?'
Produces a validated PlanUpdate schema strictly bounded by the learner's time budget and prerequisites.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput
from pydantic_ai.messages import ModelMessage, RetryPromptPart

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

logger = logging.getLogger(__name__)


def log_validation_retries(messages: list[ModelMessage]) -> None:
    """Log validation locations and safe diagnostic messages without input values."""
    for message in messages:
        for part in getattr(message, "parts", []):
            if not isinstance(part, RetryPromptPart):
                continue
            if isinstance(part.content, str):
                reason = part.content
            else:
                details = []
                for error in part.content:
                    location = ".".join(str(item) for item in error.get("loc", ())) or "output"
                    error_type = error.get("type", "validation_error")
                    message_text = error.get("msg", "Output did not match the schema.")
                    details.append(f"field={location} type={error_type} reason={message_text}")
                reason = "; ".join(details) or "Output did not match the schema."
            logger.warning("Planning output retry: %s", reason)


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
    allow_roadmap_changes: bool


class AgentPlanUpdate(BaseModel):
    """Strict model-facing output contract; persisted state retains safe defaults."""

    daily_allocation_minutes: int = Field(gt=0, le=240)
    ordered_items: list[PlanItem] = Field(min_length=1)
    adaptation_rationale: str = Field(min_length=1)
    roadmap_adjustments: list[str] = Field(default_factory=list)
    roadmap_concept_ids: list[str] = Field(
        min_length=1,
        description=(
            "Ordered goal-relevant curriculum concept IDs selected by the Agent for complete "
            "goal coverage. Add more concepts whenever coverage requires them."
        ),
    )
    roadmap_coverage_rationale: str = Field(
        min_length=1,
        description=(
            "Name the capabilities required by the goal and explain why the selected roadmap "
            "covers them without material gaps."
        ),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


PLANNING_SYSTEM_PROMPT = """You are the GoalCoach Adaptive Curriculum Planner for Mandarin Chinese learners.
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
   - `roadmap_concept_ids` is the learner's multi-session curriculum path. It is NOT today's plan.
   - Produce a goal-complete, multi-stage roadmap. Do not limit roadmap length to today's time
     budget or copy only `ordered_items`. Do not include the full catalog by default.
   - Cover the major knowledge and communication capabilities required to finish the free-form goal.
   - Decide the final roadmap size yourself from goal coverage; include every concept that is
     genuinely needed for the learner's stated goal.
   - Before returning, verify that omitting any unselected concept would not leave a material gap in
     the learner's ability to accomplish the goal.
   - Provide a specific `roadmap_coverage_rationale` naming the capabilities required by the goal
     and explaining why the selected concepts cover them without material gaps.
   - Order the selected concepts by learning sequence and keep prerequisites before dependents.
   - Reason directly from the goal and each concept's communicative purpose; do not use fixed goal categories.
   - `ordered_items` is only today's budget-bounded subset of this roadmap. Every daily item must
     also appear in `roadmap_concept_ids`.
7. Cross-Session Continuity:
   - Use the compact learning history as evidence when choosing review, remediation, and new work.
   - Avoid needless immediate repetition, but repeat a concept when its outcome or error evidence justifies it.
"""

planning_agent = Agent(
    model=get_openrouter_model(),
    deps_type=PlanningDeps,
    output_type=ToolOutput(
        AgentPlanUpdate,
        name="goalcoach_plan_update",
        description=(
            "Return one GoalCoach PlanUpdate as strict JSON. roadmap_concept_ids must be a "
            "goal-complete ordered list of unique curriculum concept IDs, and "
            "roadmap_coverage_rationale must explain complete goal coverage."
        ),
    ),
    output_retries=get_output_retries(),
    system_prompt=PLANNING_SYSTEM_PROMPT,
)


@planning_agent.output_validator
def validate_planning_output(
    ctx: RunContext[PlanningDeps], output: AgentPlanUpdate
) -> AgentPlanUpdate:
    """Require an agent-authored, valid, multi-session roadmap before persistence."""
    curriculum_ids = [
        concept.concept_id for concept in ctx.deps.content_service.list_all_concepts()
    ]
    valid_roadmap = validate_agent_roadmap(output.roadmap_concept_ids, curriculum_ids)
    if len(valid_roadmap) != len(output.roadmap_concept_ids):
        raise ModelRetry(
            "field=roadmap_concept_ids: contains unknown or duplicate concept IDs. "
            "Return valid unique IDs."
        )
    if not ctx.deps.allow_roadmap_changes and valid_roadmap != ctx.deps.state.roadmap_concept_ids:
        # The long-term roadmap is persisted learner state. Requiring the model
        # to echo it byte-for-byte wastes output retries and makes the daily
        # plan needlessly brittle.
        output.roadmap_concept_ids = list(ctx.deps.state.roadmap_concept_ids)
    if not output.roadmap_coverage_rationale.strip():
        raise ModelRetry(
            "field=roadmap_coverage_rationale: required. Explain goal capabilities and roadmap coverage."
        )
    daily_ids = {item.concept_id for item in output.ordered_items}
    if not daily_ids.issubset(set(valid_roadmap)):
        raise ModelRetry(
            "field=ordered_items[].concept_id: every daily concept must also appear in "
            "roadmap_concept_ids."
        )
    required_remedial = sorted(
        (
            (concept_id, count)
            for concept_id, count in ctx.deps.state.remediation_counters.items()
            if count >= 2 and concept_id in valid_roadmap
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    if required_remedial:
        first = output.ordered_items[0]
        if first.kind != PlanItemKind.REMEDIAL or first.concept_id != required_remedial[0][0]:
            raise ModelRetry(
                "field=ordered_items[0].kind, ordered_items[0].concept_id: the first Daily Plan "
                "item must remediate the highest-priority unresolved concept."
            )
    return output


def resolve_active_level(state: LearnerState, content_service: ContentService) -> int:
    """Determine the learner's active reachable HSK level window based on their current mastery.

    A higher level is unlocked only when all concepts of the current level have been studied and
    have achieved acceptable mastery (>= 0.50).
    """
    target_level = state.goal.target_hsk_level if state.goal else 1
    # Check levels from 1 up to target_level
    for level in range(1, target_level):
        level_concepts = content_service.list_all_concepts(hsk_level=level)
        if not level_concepts:
            continue
        # If any concept in this level has not reached mastery, stay at this level
        is_level_completed = all(
            c.concept_id in state.mastery and state.mastery[c.concept_id].mastery_score >= 0.50
            for c in level_concepts
        )
        if not is_level_completed:
            return level
    return target_level


@planning_agent.tool
def get_curriculum_catalog(ctx: RunContext[PlanningDeps]) -> list[dict[str, Any]]:
    """List available curriculum concepts up to the learner's active reachable HSK level window."""
    active_level = resolve_active_level(ctx.deps.state, ctx.deps.content_service)
    concepts = ctx.deps.content_service.list_all_concepts(max_hsk_level=active_level)
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
            "hsk_level": c.hsk_level,
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
        *,
        allow_roadmap_changes: bool = False,
    ) -> PlanUpdate:
        """Invokes the Planning Agent with fallback to deterministic heuristic rules."""
        deps = PlanningDeps(
            state=state,
            content_service=content_service,
            enable_prerequisites=self.enable_prerequisites,
            allow_roadmap_changes=allow_roadmap_changes,
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
        active_level = resolve_active_level(state, content_service)

        prompt = (
            f"Learner Goal: {state.goal.title if state.goal else 'HSK1'}\n"
            f"Current Active Reachable Level: HSK {active_level}\n"
            f"Daily Time Budget: {available_minutes} minutes\n"
            f"Needs Replanning: {state.needs_replanning}\n"
            f"Prerequisite Enforcement Enabled: {self.enable_prerequisites}\n"
            f"Roadmap Changes Allowed: {allow_roadmap_changes}\n"
            f"Remediated Today: {remediated_summary}\n"
            f"Studied Today: {studied_summary}\n"
            f"Current Mastery: {mastery_summary}\n"
            f"Active Errors: {error_summary}\n"
            f"Recent Cross-Session Learning History:\n{history_summary}\n"
            f"Today Studied Concepts (do not repeat today): {state.today_studied_concept_ids}\n"
            f"Today Remediated Concepts: {state.today_remediated_concept_ids}\n"
            "Rules for planning:\n"
            "1. If the learner has no mastery, schedule 'new' concepts unlocked by prerequisites (start with the first concept).\n"
            "2. Do NOT schedule concepts that have already been studied today.\n"
            "3. If the learner has errors or needs_replanning is True, prioritize 'remedial' items on weak concepts.\n"
            "Generate today's optimal PlanUpdate conforming to the schema. "
            f"Select concepts from the curriculum catalog within the active level window (up to HSK {active_level}). "
            "The roadmap must cover multiple future sessions; only ordered_items is constrained by today's time budget."
        )

        try:
            result, provider = await run_with_fallback(
                self.agent,
                prompt,
                deps=deps,
                component="planning_agent",
            )
            log_validation_retries(result.all_messages() if hasattr(result, "all_messages") else [])
            plan_update = PlanUpdate.model_validate(result.output.model_dump(), strict=False)
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

            try:
                reachable_concepts = content_service.list_all_concepts(max_hsk_level=active_level)
            except TypeError:
                reachable_concepts = content_service.list_all_concepts()
            valid_active_ids = {c.concept_id for c in reachable_concepts}
            curriculum_ids = [c.concept_id for c in content_service.list_all_concepts()]
            proposed_roadmap_ids = validate_agent_roadmap(
                plan_update.roadmap_concept_ids, curriculum_ids
            )
            if not allow_roadmap_changes and state.roadmap_concept_ids:
                proposed_roadmap_ids = list(state.roadmap_concept_ids)
                plan_update.roadmap_concept_ids = proposed_roadmap_ids
            validated_items = [
                item
                for item in plan_update.ordered_items
                if item.concept_id in valid_active_ids
                and item.concept_id not in state.today_studied_concept_ids
            ]
            daily_ids = list(dict.fromkeys(item.concept_id for item in validated_items))
            if not proposed_roadmap_ids or not set(daily_ids).issubset(set(proposed_roadmap_ids)):
                raise AgentOutputError(
                    "Planning Agent did not return a complete valid roadmap; existing roadmap was preserved."
                )
            if not allow_roadmap_changes:
                if not state.roadmap_concept_ids:
                    plan_update.roadmap_concept_ids = proposed_roadmap_ids
                elif proposed_roadmap_ids != state.roadmap_concept_ids:
                    raise AgentOutputError(
                        "Daily replanning attempted to change the long-term roadmap; existing roadmap was preserved."
                    )
            if not plan_update.roadmap_coverage_rationale.strip():
                raise AgentOutputError(
                    "Planning Agent omitted the required roadmap coverage rationale."
                )
            required_remedial = sorted(
                (
                    (concept_id, count)
                    for concept_id, count in state.remediation_counters.items()
                    if count >= 2 and concept_id in proposed_roadmap_ids
                ),
                key=lambda item: item[1],
                reverse=True,
            )
            if required_remedial:
                first = validated_items[0] if validated_items else None
                if (
                    first is None
                    or first.kind != PlanItemKind.REMEDIAL
                    or first.concept_id != required_remedial[0][0]
                ):
                    raise AgentOutputError(
                        "Planning Agent did not prioritize the required remediation item."
                    )
            plan_update.roadmap_concept_ids = proposed_roadmap_ids
            plan_update.metadata.update(
                {
                    "roadmap_concept_count": len(plan_update.roadmap_concept_ids),
                    "roadmap_source": "planning_agent",
                }
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
                        content_service.get_all_prerequisites() if self.enable_prerequisites else {}
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
        active_level = resolve_active_level(state, content_service)
        try:
            concepts = content_service.list_all_concepts(max_hsk_level=active_level)
        except TypeError:
            concepts = content_service.list_all_concepts()
        if not concepts:
            concepts = content_service.list_all_concepts()
        if not concepts:
            raise AgentOutputError(
                "No curriculum concepts are available for deterministic planning"
            )
        concept_by_id = {concept.concept_id: concept for concept in concepts}
        catalog_ids = [concept.concept_id for concept in concepts]
        roadmap_ids = state.roadmap_concept_ids or catalog_ids
        roadmap_ids = validate_agent_roadmap(roadmap_ids, catalog_ids)
        roadmap_id_set = set(roadmap_ids)
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
                if error.concept_id in roadmap_id_set
                and error.concept_id not in state.today_remediated_concept_ids
            )
        )
        due_ids = [
            concept_id
            for concept_id, mastery in state.mastery.items()
            if concept_id in roadmap_id_set and mastery.is_review_due()
        ]
        new_ids = [
            concept_id
            for concept_id in roadmap_ids
            if concept_id not in state.mastery and concept_id not in state.today_studied_concept_ids
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
            concept = concept_by_id[roadmap_ids[0]]
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
            roadmap_adjustments=["Deterministic fallback retained the existing Agent roadmap."],
            roadmap_concept_ids=roadmap_ids,
            roadmap_coverage_rationale=(
                "Fallback reuses the previously validated roadmap selected for this goal."
            ),
            metadata={
                "provider": "deterministic",
                "fallback_used": True,
                "notice": notice,
                "roadmap_concept_count": len(roadmap_ids),
                "roadmap_source": "existing_agent_roadmap",
            },
        )

    def _heuristic_fallback(
        self,
        state: LearnerState,
        content_service: ContentService,
        available_minutes: int = 20,
        *,
        notice: str = "Deterministic planning fallback used.",
    ) -> PlanUpdate:
        return self._deterministic_fallback(
            state, content_service, available_minutes, notice=notice
        )


__all__ = [
    "PLANNING_SYSTEM_PROMPT",
    "PlanningDeps",
    "PlanningWorker",
    "planning_agent",
    "resolve_active_level",
    "validate_agent_roadmap",
    "validate_planning_output",
]
