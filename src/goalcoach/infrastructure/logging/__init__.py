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
from goalcoach.infrastructure.logging.formatters import DevelopmentFormatter, JSONFormatter

__all__ = [
    "REDACTED_SUBSTITUTION",
    "ContextFilter",
    "DevelopmentFormatter",
    "JSONFormatter",
    "SecretScrubbingFilter",
    "bind_context",
    "bind_request_id",
    "clear_context",
    "configure_logging",
    "current_request_id",
    "get_context",
    "reset_context",
    "reset_request_id",
    "scrub_data",
    "scrub_sensitive_text",
    "set_context",
]
