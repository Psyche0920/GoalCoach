"""Compose atomic Jev choices into a validated, curriculum-grounded learning plan."""

from __future__ import annotations

import json
import logging

from goalcoach.agents.planning_agent import PlanningWorker, RemediationPolicy, resolve_active_level
from goalcoach.application.decisions.contracts import (
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionClient,
    DecisionError,
    DecisionRequest,
)
from goalcoach.domain.enums import PlanItemKind
from goalcoach.domain.models import LearnerState, PlanItem, PlanUpdate
from goalcoach.infrastructure.persistence.content_service import ContentService

logger = logging.getLogger(__name__)


class JevPlanningWorker:
    def __init__(self, client: DecisionClient, fallback: PlanningWorker) -> None:
        self._client = client
        self._fallback = fallback

    @staticmethod
    def _priority_score(answer: ChoiceAnswer) -> float:
        """Rank courses by expected priority without rejecting uncertain choices."""
        return 2 * answer.probabilities.get("high", 0.0) + answer.probabilities.get("medium", 0.0)

    async def create_plan(
        self,
        state: LearnerState,
        content_service: ContentService,
        *,
        allow_roadmap_changes: bool = False,
    ) -> PlanUpdate:
        try:
            return await self._create_plan(state, content_service, allow_roadmap_changes)
        except DecisionError as exc:
            logger.warning("Jev planning fallback: %s", exc)
            # Uncertain free-form goals and unavailable Jev retain the existing agent path.
            result = await self._fallback.create_plan(
                state, content_service, allow_roadmap_changes=allow_roadmap_changes
            )
            result.metadata["jev_fallback"] = True
            return result

    async def _create_plan(
        self, state: LearnerState, content: ContentService, allow_changes: bool
    ) -> PlanUpdate:
        level = resolve_active_level(state, content)
        concepts = content.list_all_concepts(max_hsk_level=level)
        by_id = {c.concept_id: c for c in concepts}
        if not concepts:
            raise DecisionError("No curriculum candidates")
        rebuild = allow_changes or not state.roadmap_concept_ids
        candidates = (
            concepts
            if rebuild
            else [by_id[cid] for cid in state.roadmap_concept_ids if cid in by_id]
        )
        context = json.dumps(
            {
                "goal": state.goal.title if state.goal else "HSK 1 Mandarin",
                "mastery": {
                    cid: {
                        "score": m.mastery_score,
                        "retention": m.current_retention(),
                        "due": m.is_review_due(),
                    }
                    for cid, m in state.mastery.items()
                },
                "remediation": state.remediation_counters,
            },
            ensure_ascii=False,
        )
        questions: dict[str, ChoiceQuestion] = {}
        course_evidence: dict[str, str] = {}
        for i, c in enumerate(candidates):
            evidence = json.dumps(
                {
                    "id": c.concept_id,
                    "purpose": c.communicative_goal,
                    "grammar": c.grammar_focus,
                    "vocabulary": c.vocabulary_focus,
                },
                ensure_ascii=False,
            )
            course_evidence[c.concept_id] = evidence
            if rebuild:
                questions[f"include_{i}"] = ChoiceQuestion(
                    instructions=f"For the learner goal, is this course directly necessary, useful but optional, or irrelevant? Mark required only when its taught capability is needed to accomplish the stated goal. Do not mark a course required just because it comes earlier in the curriculum or could be generally useful. Judge relevance to the full goal, not today's budget. Course: {evidence}",
                    criteria={
                        "required": "Directly needed to accomplish the stated goal",
                        "optional": "Related or useful, but not needed for the stated goal",
                        "irrelevant": "Does not advance this goal",
                    },
                )
            questions[f"priority_{i}"] = ChoiceQuestion(
                instructions=f"How urgent is studying this course now, given the goal and learner state? Course: {evidence}",
                criteria={
                    "high": "Most valuable next work",
                    "medium": "Useful after higher priority work",
                    "low": "Can wait",
                },
            )
            questions[f"kind_{i}"] = ChoiceQuestion(
                instructions=f"Choose the pedagogical purpose of studying this course now. Course: {evidence}",
                criteria={
                    "new": "Introduce an unstudied capability",
                    "review": "Retrieve previously studied knowledge",
                    "remedial": "Address current errors or confusion",
                },
            )
            questions[f"duration_{i}"] = ChoiceQuestion(
                instructions=f"Choose a bite-sized practice duration appropriate for the current learner and course: {evidence}",
                criteria={
                    "3": "Brief retrieval or reminder",
                    "4": "Focused practice",
                    "5": "New learning or substantive remediation",
                },
            )
        response = await self._client.decide(DecisionRequest(state=context, questions=questions))
        selected = {
            c.concept_id
            for i, c in enumerate(candidates)
            if not rebuild or response.answers[f"include_{i}"].choice == "required"
        }
        added_missing_ids: list[str] = []
        if rebuild:
            unselected = [c for c in candidates if c.concept_id not in selected]
            if unselected:
                missing_questions = {
                    f"missing_{i}": ChoiceQuestion(
                        instructions=(
                            "Does this course teach a capability necessary for the learner goal "
                            "that the selected courses do not yet cover? Add it only for a "
                            "specific missing goal capability, not for general usefulness or "
                            f"curriculum order. Course: {course_evidence[c.concept_id]}"
                        ),
                        criteria={
                            "skip": "No necessary goal capability is missing from the selected courses",
                            "add": "This course supplies a necessary goal capability still missing",
                        },
                    )
                    for i, c in enumerate(unselected)
                }
                missing_response = await self._client.decide(
                    DecisionRequest(
                        state=json.dumps(
                            {
                                "goal": state.goal.title if state.goal else "HSK 1 Mandarin",
                                "selected_courses": [
                                    {
                                        "id": c.concept_id,
                                        "purpose": c.communicative_goal,
                                    }
                                    for c in candidates
                                    if c.concept_id in selected
                                ],
                            },
                            ensure_ascii=False,
                        ),
                        questions=missing_questions,
                    )
                )
                added_missing_ids = [
                    c.concept_id
                    for i, c in enumerate(unselected)
                    if missing_response.answers[f"missing_{i}"].choice == "add"
                ]
                selected.update(added_missing_ids)
        if not selected:
            raise DecisionError("Goal has no supported course coverage")
        graph = content.get_all_prerequisites() if self._fallback.enable_prerequisites else {}
        if rebuild:

            def add_dependencies(cid: str, visiting: set[str]) -> None:
                if cid in visiting:
                    raise DecisionError("Curriculum dependency cycle")
                for dependency in graph.get(cid, frozenset()):
                    if dependency not in by_id:
                        raise DecisionError("Unavailable roadmap prerequisite")
                    selected.add(dependency)
                    add_dependencies(dependency, visiting | {cid})

            for cid in tuple(selected):
                add_dependencies(cid, set())
            roadmap: list[str] = []
            pending = set(selected)
            while pending:
                ready = [cid for cid in pending if not (set(graph.get(cid, ())) & pending)]
                if not ready:
                    raise DecisionError("Curriculum dependency cycle")
                ready.sort(key=lambda cid: (by_id[cid].sequence_no, cid))
                roadmap.extend(ready)
                pending.difference_update(ready)
        else:
            roadmap = list(state.roadmap_concept_ids)
        policy = RemediationPolicy.from_state(state, roadmap)
        unavailable = set(state.today_studied_concept_ids) | set(state.today_remediated_concept_ids)
        candidate_index = {c.concept_id: i for i, c in enumerate(candidates)}
        decisions = {
            c.concept_id: (
                response.answers[f"priority_{i}"].choice,
                response.answers[f"kind_{i}"].choice,
            )
            for i, c in enumerate(candidates)
        }
        eligible = []
        for cid in roadmap:
            if cid not in by_id or cid in policy.required_concept_ids:
                continue
            if cid in unavailable:
                continue
            kind = PlanItemKind(decisions.get(cid, ("medium", "new"))[1])
            if (
                kind == PlanItemKind.NEW
                and self._fallback.enable_prerequisites
                and not all(
                    p in state.today_remediated_concept_ids
                    or (p in state.mastery and state.mastery[p].mastery_score >= 0.5)
                    for p in graph.get(cid, ())
                )
            ):
                continue
            eligible.append(cid)
        eligible.sort(
            key=lambda cid: (
                -self._priority_score(response.answers[f"priority_{candidate_index[cid]}"]),
                roadmap.index(cid),
            )
        )
        budget = (
            state.active_session.planned_minutes
            if state.active_session
            else (state.goal.daily_available_minutes if state.goal else 20)
        )
        items: list[PlanItem] = []
        remaining = budget
        for cid in list(policy.required_concept_ids) + eligible:
            if cid not in by_id or remaining < 3:
                continue
            index = candidate_index.get(cid)
            preferred = (
                int(response.answers[f"duration_{index}"].choice) if index is not None else 5
            )
            minutes = min(preferred, remaining)
            kind = (
                PlanItemKind.REMEDIAL
                if cid in policy.required_concept_ids
                else PlanItemKind(decisions.get(cid, ("medium", "new"))[1])
            )
            items.append(
                PlanItem(
                    concept_id=cid,
                    kind=kind,
                    objective=by_id[cid].communicative_goal[:500] or by_id[cid].title_en,
                    estimated_minutes=minutes,
                )
            )
            remaining -= minutes
        if not items or not policy.has_required_first_item(items):
            raise DecisionError("No valid daily work")
        roadmap_rationale = state.roadmap_coverage_rationale
        if rebuild:
            roadmap_rationale = "Selected curriculum capabilities needed for your goal."
            if added_missing_ids:
                added_descriptions = ", ".join(
                    f"{cid} ({by_id[cid].communicative_goal})" for cid in added_missing_ids
                )
                roadmap_rationale += f" Added missing courses: {added_descriptions}."
            if graph:
                roadmap_rationale += " Prerequisite topics preserve the learning sequence."
        return PlanUpdate(
            daily_allocation_minutes=sum(i.estimated_minutes for i in items),
            ordered_items=items,
            adaptation_rationale="Selected from your roadmap using current learning priorities, review needs, and unresolved errors.",
            roadmap_concept_ids=roadmap,
            roadmap_coverage_rationale=roadmap_rationale,
            metadata={
                "provider": "typesafe:" + response.model,
                "roadmap_source": "jev",
                "fallback_used": False,
                "jev_added_missing_course_ids": added_missing_ids,
            },
        )
