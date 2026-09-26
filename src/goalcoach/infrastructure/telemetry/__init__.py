"""Privacy-safe structured telemetry for model executions."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar, Token
from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

logger = logging.getLogger("goalcoach.agent_telemetry")

_request_id: ContextVar[str | None] = ContextVar("goalcoach_request_id", default=None)


@dataclass(frozen=True, slots=True)
class AgentTelemetryEvent:
    """One model attempt without prompts, answers, credentials, or learner content."""

    request_id: str
    component: str
    provider: str
    model: str
    prompt_version: str
    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    validation_succeeded: bool
    fallback_used: bool
    failure_kind: str | None = None


def bind_request_id(request_id: str) -> Token[str | None]:
    """Bind an API correlation ID to the current asynchronous request context."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the previous correlation context."""
    _request_id.reset(token)


def current_request_id() -> str:
    """Return the API request ID, or a local execution ID outside HTTP requests."""
    return _request_id.get() or str(uuid4())


def token_usage(result: Any) -> tuple[int | None, int | None]:
    """Read PydanticAI usage defensively across supported result versions."""
    usage_accessor = getattr(result, "usage", None)
    usage = usage_accessor() if callable(usage_accessor) else usage_accessor
    if usage is None:
        return None, None
    return getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None)


def emit_agent_telemetry(event: AgentTelemetryEvent) -> None:
    """Emit a stable JSON record suitable for a log or tracing collector."""
    logger.info(json.dumps(asdict(event), separators=(",", ":"), sort_keys=True))


__all__ = [
    "AgentTelemetryEvent",
    "bind_request_id",
    "current_request_id",
    "emit_agent_telemetry",
    "reset_request_id",
    "token_usage",
]
