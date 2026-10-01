"""Privacy-safe structured telemetry for model executions and financial ledger events."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

from goalcoach.domain.telemetry import (
    AgentLifecycleStage,
    AgentTelemetryRecord,
    CostAccountingRecord,
)
from goalcoach.infrastructure.logging.context import (
    bind_request_id,
    current_request_id,
    reset_request_id,
)
from goalcoach.infrastructure.logging.sinks import (
    get_cost_logger,
    get_telemetry_logger,
)

logger = logging.getLogger("goalcoach.agent_telemetry")


@dataclass(frozen=True, slots=True)
class AgentTelemetryEvent:
    """Legacy model attempt record preserved for backward compatibility."""

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
    """Legacy emitter for AgentTelemetryEvent."""
    logger.info(json.dumps(asdict(event), separators=(",", ":"), sort_keys=True))


def emit_telemetry_record(record: AgentTelemetryRecord) -> None:
    """Emit an AgentTelemetryRecord exclusively to logs/agent_telemetry.jsonl."""
    get_telemetry_logger().info(record.model_dump_json())


def emit_cost_record(record: CostAccountingRecord) -> None:
    """Emit a CostAccountingRecord exclusively to logs/cost_accounting.jsonl."""
    get_cost_logger().info(record.model_dump_json())


__all__ = [
    "AgentLifecycleStage",
    "AgentTelemetryEvent",
    "AgentTelemetryRecord",
    "CostAccountingRecord",
    "bind_request_id",
    "current_request_id",
    "emit_agent_telemetry",
    "emit_cost_record",
    "emit_telemetry_record",
    "reset_request_id",
    "token_usage",
]
