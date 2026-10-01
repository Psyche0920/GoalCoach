"""Enterprise structured logging and execution context observability for GoalCoach."""

from __future__ import annotations

from goalcoach.infrastructure.logging.config import configure_logging
from goalcoach.infrastructure.logging.context import (
    bind_context,
    bind_request_id,
    clear_context,
    current_request_id,
    get_context,
    reset_context,
    reset_request_id,
    set_context,
)
from goalcoach.infrastructure.logging.filters import (
    REDACTED_SUBSTITUTION,
    ContextFilter,
    SecretScrubbingFilter,
    scrub_data,
    scrub_sensitive_text,
)
from goalcoach.infrastructure.logging.formatters import (
    DevelopmentFormatter,
    JSONFormatter,
    NDJSONFormatter,
)
from goalcoach.infrastructure.logging.sinks import (
    BACKEND_LOGGER_NAME,
    COST_LOGGER_NAME,
    TELEMETRY_LOGGER_NAME,
    get_backend_logger,
    get_cost_logger,
    get_telemetry_logger,
    setup_isolated_sinks,
    start_logging_queue,
    stop_logging_queue,
)

__all__ = [
    "BACKEND_LOGGER_NAME",
    "COST_LOGGER_NAME",
    "REDACTED_SUBSTITUTION",
    "TELEMETRY_LOGGER_NAME",
    "ContextFilter",
    "DevelopmentFormatter",
    "JSONFormatter",
    "NDJSONFormatter",
    "SecretScrubbingFilter",
    "bind_context",
    "bind_request_id",
    "clear_context",
    "configure_logging",
    "current_request_id",
    "get_backend_logger",
    "get_context",
    "get_cost_logger",
    "get_telemetry_logger",
    "reset_context",
    "reset_request_id",
    "scrub_data",
    "scrub_sensitive_text",
    "set_context",
    "setup_isolated_sinks",
    "start_logging_queue",
    "stop_logging_queue",
]
