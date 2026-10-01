"""Domain models for agent telemetry and LLM cost accounting."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


class AgentLifecycleStage(StrEnum):
    """Lifecycle stages for agent execution and tool interactions."""

    STARTED = "started"
    TOOL_CALLED = "tool_called"
    TOOL_RETURNED = "tool_returned"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTelemetryRecord(BaseModel):
    """Event emitted exclusively to logs/agent_telemetry.jsonl."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    trace_id: str
    run_id: str
    parent_run_id: str | None = None
    agent_name: str
    stage: AgentLifecycleStage
    learner_id: UUID | str | None = None
    concept_id: str | None = None
    tool_name: str | None = None
    tool_latency_ms: float | None = None
    execution_latency_ms: float | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class CostAccountingRecord(BaseModel):
    """Financial ledger record emitted exclusively to logs/cost_accounting.jsonl."""

    model_config = ConfigDict(frozen=True)

    record_id: UUID = Field(default_factory=uuid4)
    trace_id: str
    run_id: str
    learner_id: UUID | str | None = None
    agent_name: str
    provider: str  # e.g., "openrouter" or "ollama"
    model_name: str
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(ge=0)
    input_cost_usd: float = Field(ge=0.0)
    output_cost_usd: float = Field(ge=0.0)
    total_cost_usd: float = Field(ge=0.0)
    is_fallback: bool = False
    budget_exceeded: bool = False
    cumulative_session_cost_usd: float = Field(default=0.0, ge=0.0)
    timestamp: datetime = Field(default_factory=utc_now)


__all__ = [
    "AgentLifecycleStage",
    "AgentTelemetryRecord",
    "CostAccountingRecord",
    "utc_now",
]
