"""Privacy-safe structured telemetry for model executions."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

from goalcoach.infrastructure.logging.context import (
    bind_request_id,
    current_request_id,
    reset_request_id,
)

logger = logging.getLogger("goalcoach.agent_telemetry")


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
