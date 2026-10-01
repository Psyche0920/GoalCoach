"""Select canonical teaching material with Jev; keep open questions with the tutor."""

from __future__ import annotations

import json
import logging

from goalcoach.agents.teaching_agent import TeachingWorker
from goalcoach.application.decisions.contracts import (
    ChoiceQuestion,
    DecisionClient,
    DecisionError,
    DecisionRequest,
)
from goalcoach.domain.enums import TeachingActionKind
from goalcoach.domain.models import LearnerState, TeachingAction
from goalcoach.infrastructure.persistence.content_service import ContentService

logger = logging.getLogger(__name__)


class JevTeachingWorker:
    def __init__(self, client: DecisionClient, fallback: TeachingWorker) -> None:
        self._client = client
        self._fallback = fallback

    async def teach_concept(
        self,
        concept_id: str,
        state: LearnerState,
        content_service: ContentService,
        failed_attempts: int = 0,
        learner_query: str | None = None,
        excluded_exercise_id: str | None = None,
        target_exercise_id: str | None = None,
    ) -> TeachingAction:
        if not learner_query:
            try:
                return await self._teach(
                    concept_id,
                    state,
                    content_service,
                    failed_attempts,
                    excluded_exercise_id,
                    target_exercise_id,
                )
            except DecisionError as exc:
                logger.warning("Jev teaching fallback: %s", exc)
        action = await self._fallback.teach_concept(
            concept_id,
            state,
            content_service,
            failed_attempts=failed_attempts,
            learner_query=learner_query,
            excluded_exercise_id=excluded_exercise_id,
            target_exercise_id=target_exercise_id,
        )
        if not learner_query:
            action.metadata["jev_fallback"] = True
        return action

    async def _teach(
        self,
        cid: str,
        state: LearnerState,
        content: ContentService,
        failures: int,
        excluded: str | None,
        target: str | None,
    ) -> TeachingAction:
        concept = content.get_concept(cid)
        cards = content.get_teaching_cards(cid)
        exercises = content.get_exercises_for_concept(cid, limit=10, randomize=False)
        if not concept or not cards or not exercises:
            raise DecisionError("No canonical teaching candidates")
        completed = set(state.today_completed_exercise_ids)
        recent = {
            t.exercise_id for t in state.agent_history.recent_teaching_turns if t.concept_id == cid
        }
        if target:
            exercises = [e for e in exercises if str(e.exercise_id) == target]
        else:
            valid = [
                e
                for e in exercises
                if str(e.exercise_id) != excluded and str(e.exercise_id) not in completed
            ]
            fresh = [e for e in valid if str(e.exercise_id) not in recent]
            exercises = fresh or valid
        if not exercises:
            raise DecisionError("No eligible exercises")
        questions = {
            "strategy": ChoiceQuestion(
                instructions="Select the teaching strategy appropriate to current errors, attempts, and learning history.",
                criteria={
                    "EXPLANATION": "Introduce the verified material",
                    "HINT": "Give a brief reminder before practice",
                    "CONTRAST_EXAMPLE": "Show another example to address confusion",
                    "RETRY": "Break the verified material into smaller steps",
                    "DIALOGUE": "Practice a dialogue supported by the selected material",
                },
            )
        }
        if len(cards) > 1:
            questions["card"] = ChoiceQuestion(
                instructions="Choose the teaching card most useful for the learner's current understanding and errors.",
                criteria={
                    f"c{i}": json.dumps(
                        {
                            "word": c.prompt_zh,
                            "meaning": c.meaning_en,
                            "explanation": c.explanation_en,
                            "example": c.example_zh,
                        },
                        ensure_ascii=False,
                    )
                    for i, c in enumerate(cards[:255])
                },
            )
        if len(exercises) > 1:
            questions["exercise"] = ChoiceQuestion(
                instructions="Choose the next exercise that best develops this concept and addresses current errors. Prefer relevant mistake practice during remediation.",
                criteria={
                    f"e{i}": json.dumps(
                        {
                            "id": str(e.exercise_id),
                            "prompt": e.prompt,
                            "instruction": e.instruction,
                            "type": e.exercise_type,
                            "previous_mistake": str(e.exercise_id)
                            in state.today_mistake_exercise_ids,
                        },
                        ensure_ascii=False,
                    )
                    for i, e in enumerate(exercises)
                },
            )
        result = await self._client.decide(
            DecisionRequest(
                state=json.dumps(
                    {
                        "goal": state.goal.title if state.goal else "HSK1",
                        "concept": concept.communicative_goal,
                        "failed_attempts": failures,
                        "exercises": [
                            {
                                "prompt": e.prompt,
                                "instruction": e.instruction,
                                "type": e.exercise_type,
                            }
                            for e in exercises
                        ],
                        "mastery": state.mastery[cid].mastery_score if cid in state.mastery else 0,
                        "errors": [e.code for e in state.error_profile if e.concept_id == cid],
                        "history": [
                            t.model_dump(mode="json")
                            for t in state.agent_history.recent_teaching_turns
                            if t.concept_id == cid
                        ][-3:],
                    },
                    ensure_ascii=False,
                ),
                questions=questions,
            )
        )
        card = cards[int(result.answers["card"].choice[1:])] if "card" in questions else cards[0]
        exercise = (
            exercises[int(result.answers["exercise"].choice[1:])]
            if "exercise" in questions
            else exercises[0]
        )
        strategy = TeachingActionKind(result.answers["strategy"].choice)

        def cell(value: str | None) -> str:
            return (value or "").replace("|", "\\|").replace("\n", " ")

        table = f"| Character | Pinyin | Meaning |\n|---|---|---|\n| {cell(card.prompt_zh)} | {cell(card.pinyin)} | {cell(card.meaning_en)} |"
        explanation = card.explanation_en or concept.communicative_goal
        example = (
            f"{card.example_zh} ({card.example_pinyin or ''}) — {card.example_en or ''}"
            if card.example_zh
            else ""
        )
        if strategy == TeachingActionKind.HINT:
            text = f"{explanation}\n\n{table}"
        elif strategy == TeachingActionKind.RETRY:
            text = f"1. Review: {explanation}\n\n{table}\n\n2. Example: {example}\n\n3. {exercise.instruction or 'Try the practice below.'}"
        else:
            text = f"{explanation}\n\n{table}" + (f"\n\nExample: {example}" if example else "")
        action = TeachingAction(
            action_kind=strategy,
            concept_id=cid,
            content=text,
            history_summary=f"Studied {concept.title_en} with {strategy.value.lower()} and curriculum practice."[
                :240
            ],
            pinyin=card.pinyin,
            metadata={
                "provider": "typesafe:" + result.model,
                "fallback_used": False,
                "teaching_card_id": str(card.card_id),
                "decision_confidence": result.answers["strategy"].confidence,
            },
        )
        return TeachingWorker._attach_selected_exercise(action, exercise)
