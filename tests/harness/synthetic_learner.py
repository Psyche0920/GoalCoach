"""Headless Synthetic Learner Swarm Engine.

Simulates multi-turn learner personas driving the FastAPI orchestration boundaries
directly via ASGI or HTTP with strict trace propagation and zero state pollution.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

import httpx

logger = logging.getLogger("goalcoach.test.swarm")


class SyntheticLearner:
    """Async client driving the GoalCoach learning loop for a simulated learner."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        learner_id: str | None = None,
        persona_name: str = "GenericLearner",
        test_run_id: str | None = None,
    ) -> None:
        self.client = client
        self.learner_id = learner_id or f"learner_{uuid4().hex[:8]}"
        self.persona_name = persona_name
        self.test_run_id = test_run_id or f"run_{uuid4().hex[:8]}"

    def _default_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Test-Run-ID": self.test_run_id,
            "X-Learner-Persona": self.persona_name,
            "X-Request-ID": f"req_{uuid4().hex[:12]}",
        }

    async def post_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a typed event to POST /api/v1/events."""
        body = {
            "event_type": event_type,
            "learner_id": self.learner_id,
            "payload": payload,
        }
        res = await self.client.post(
            "/api/v1/events",
            json=body,
            headers=self._default_headers(),
        )
        res.raise_for_status()
        return res.json()

    async def create_goal(
        self,
        title: str = "Master HSK 1 Core Vocabulary",
        target_hsk_level: int = 1,
        daily_available_minutes: int = 20,
        timezone: str = "UTC",
    ) -> dict[str, Any]:
        """Create or update the learner's curriculum goal."""
        return await self.post_event(
            "GOAL_CREATED",
            {
                "title": title,
                "target_hsk_level": target_hsk_level,
                "daily_available_minutes": daily_available_minutes,
                "timezone": timezone,
            },
        )

    async def start_session(
        self,
        concept_id: str | None = None,
        plan_item_id: str | None = None,
        preferred_duration_minutes: int | None = 20,
    ) -> dict[str, Any]:
        """Signal the start of a study session."""
        return await self.post_event(
            "SESSION_STARTED",
            {
                "concept_id": concept_id,
                "plan_item_id": plan_item_id,
                "preferred_duration_minutes": preferred_duration_minutes,
            },
        )

    async def submit_answer(
        self,
        concept_id: str,
        exercise_id: str,
        answer: str,
        time_spent_seconds: int = 15,
    ) -> dict[str, Any]:
        """Submit an exercise answer."""
        return await self.post_event(
            "ANSWER_SUBMITTED",
            {
                "concept_id": concept_id,
                "exercise_id": exercise_id,
                "answer": answer,
                "time_spent_seconds": time_spent_seconds,
            },
        )

    async def request_help(
        self,
        concept_id: str,
        current_exercise_id: str | None = None,
        query: str = "Could you explain the grammar rule again?",
    ) -> dict[str, Any]:
        """Signal confusion or request tutor guidance."""
        return await self.post_event(
            "HELP_REQUESTED",
            {
                "concept_id": concept_id,
                "current_exercise_id": current_exercise_id,
                "learner_query": query,
            },
        )

    async def request_replan(self, reason: str = "Swarm stress replan trigger") -> dict[str, Any]:
        """Explicitly request a daily plan recalculation."""
        return await self.post_event(
            "REPLAN_REQUESTED",
            {"reason": reason},
        )

    async def end_session(self, additional_active_seconds: int = 60) -> dict[str, Any]:
        """Close an active study session."""
        return await self.post_event(
            "SESSION_ENDED",
            {"additional_active_seconds": additional_active_seconds},
        )

    async def get_state(self) -> dict[str, Any]:
        """Fetch current learner aggregate state."""
        res = await self.client.get(
            f"/api/v1/learners/{self.learner_id}",
            headers=self._default_headers(),
        )
        res.raise_for_status()
        return res.json()

    async def get_today_plan(self) -> dict[str, Any]:
        """Fetch today's active plan."""
        res = await self.client.get(
            f"/api/v1/learners/{self.learner_id}/today-plan",
            headers=self._default_headers(),
        )
        res.raise_for_status()
        return res.json()

    async def get_roadmap(self) -> dict[str, Any]:
        """Fetch the learner's personalized roadmap projection."""
        res = await self.client.get(
            f"/api/v1/learners/{self.learner_id}/roadmap",
            headers=self._default_headers(),
        )
        res.raise_for_status()
        return res.json()

    async def get_curriculum_concepts(self, hsk_level: int | None = None) -> list[dict[str, Any]]:
        """List active curriculum concepts."""
        params = {"hsk_level": hsk_level} if hsk_level is not None else {}
        res = await self.client.get(
            "/api/v1/curriculum/concepts",
            params=params,
            headers=self._default_headers(),
        )
        res.raise_for_status()
        return res.json()

    async def get_concept_details(self, concept_id: str) -> dict[str, Any]:
        """Fetch concept details, cards, and exercises."""
        res = await self.client.get(
            f"/api/v1/curriculum/concepts/{concept_id}",
            headers=self._default_headers(),
        )
        res.raise_for_status()
        return res.json()
