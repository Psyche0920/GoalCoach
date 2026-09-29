"""Custom formatters: Machine-readable NDJSON for production and colored console text for dev."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from goalcoach.infrastructure.logging.context import get_context

# Standard LogRecord attributes that should not be dumped into "extra"
_STANDARD_RECORD_ATTRS: frozenset[str] = frozenset(
    {
        "args",
        "context",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)

_ANSI_COLORS: dict[str, str] = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[1;31m",  # Bold Red
}
_ANSI_RESET = "\033[0m"
_ANSI_DIM = "\033[2m"


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line Newline Delimited JSON (NDJSON)."""

    def format(self, record: logging.LogRecord) -> str:
        record_message = record.getMessage()

        # Build context from record attribute or contextvars
        context_data = getattr(record, "context", None)
        if context_data is None:
            context_data = get_context()

        # Extract extra structured attributes passed in extra={...}
        extra_data: dict[str, Any] = {}
        for key, val in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and key not in context_data:
                extra_data[key] = val

        # If extra contains an "extra" dict, flatten or merge it
        if "extra" in extra_data and isinstance(extra_data["extra"], dict):
            nested_extra = extra_data.pop("extra")
            extra_data.update(nested_extra)

        now_utc = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {
            "timestamp": now_utc,
            "level": record.levelname,
            "logger": record.name,
            "message": record_message,
        }

        if context_data:
            payload["context"] = context_data

        if extra_data:
            payload["extra"] = extra_data

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False, default=str)


class DevelopmentFormatter(logging.Formatter):
    """Compact, colorized console formatter for interactive development environments."""

    def format(self, record: logging.LogRecord) -> str:
        color = _ANSI_COLORS.get(record.levelname, "")
        now_str = datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]

        context_data = getattr(record, "context", None) or get_context()
        ctx_str = ""
        if context_data:
            ctx_items = " ".join(f"{k}={v}" for k, v in sorted(context_data.items()))
            ctx_str = f" {_ANSI_DIM}[{ctx_items}]{_ANSI_RESET}"

        base_line = (
            f"{_ANSI_DIM}[{now_str}]{_ANSI_RESET} "
            f"{color}[{record.levelname:<7}]{_ANSI_RESET} "
            f"[{record.name}] {record.getMessage()}{ctx_str}"
        )

        if record.exc_info:
            base_line += f"\n{self.formatException(record.exc_info)}"

        return base_line


__all__ = [
    "DevelopmentFormatter",
    "JSONFormatter",
]
