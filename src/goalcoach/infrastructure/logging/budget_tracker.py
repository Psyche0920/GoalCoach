"""Thread-safe cumulative session budget monitor for agent LLM inference."""

from __future__ import annotations

import logging
import threading
from typing import ClassVar

logger = logging.getLogger("goalcoach.agent.budget_tracker")


class BudgetTracker:
    """Tracks and enforces cumulative LLM spending limits per session or learner."""

    _lock: ClassVar[threading.Lock] = threading.Lock()
    _sessions: ClassVar[dict[str, float]] = {}

    @classmethod
    def accumulate(
        cls,
        session_key: str,
        cost_usd: float,
        limit_usd: float | None = None,
    ) -> tuple[float, bool]:
        """Accumulate cost and return (cumulative_session_cost, budget_exceeded)."""
        from goalcoach.infrastructure.config import Settings

        resolved_limit = limit_usd if limit_usd is not None else Settings().session_cost_limit_usd

        with cls._lock:
            current = cls._sessions.get(session_key, 0.0)
            updated = round(current + cost_usd, 8)
            cls._sessions[session_key] = updated
            exceeded = updated > resolved_limit

        if exceeded and current <= resolved_limit:
            logger.warning(
                "Session budget ceiling exceeded for '%s': accumulated $%.6f USD (limit: $%.4f USD)",
                session_key,
                updated,
                resolved_limit,
            )

        return updated, exceeded

    @classmethod
    def get_cost(cls, session_key: str) -> float:
        """Return the current cumulative spend for a session."""
        with cls._lock:
            return cls._sessions.get(session_key, 0.0)

    @classmethod
    def reset(cls, session_key: str | None = None) -> None:
        """Reset accumulated cost for a specific session or all sessions."""
        with cls._lock:
            if session_key is None:
                cls._sessions.clear()
            else:
                cls._sessions.pop(session_key, None)


__all__ = ["BudgetTracker"]
