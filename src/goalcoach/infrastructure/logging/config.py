"""Idempotent logging configuration integrating standard library, filters, and formatters."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from goalcoach.infrastructure.logging.filters import ContextFilter, SecretScrubbingFilter
from goalcoach.infrastructure.logging.formatters import DevelopmentFormatter, JSONFormatter

if TYPE_CHECKING:
    from goalcoach.infrastructure.config import Settings

_CONFIGURED = False


def configure_logging(
    settings: Settings | None = None,
    log_to_file: bool | None = None,
    file_path: str | None = None,
    log_to_stream: bool = True,
) -> None:
    """Configure root and application loggers according to the active typed Settings.

    Idempotent across multiple invocations.
    """
    global _CONFIGURED
    from logging.handlers import RotatingFileHandler
    from pathlib import Path

    from goalcoach.infrastructure.config import Settings as ConfigSettings

    resolved_settings = settings or ConfigSettings()

    # Determine log level
    level_name = resolved_settings.log_level.upper()
    log_level = getattr(logging, level_name, logging.INFO)

    # Determine formatter
    fmt_choice = resolved_settings.log_format.lower()
    use_json = fmt_choice == "json" or (
        fmt_choice == "auto"
        and resolved_settings.environment.lower() in ("production", "staging", "testing", "ci")
    )

    formatter: logging.Formatter
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = DevelopmentFormatter()

    handlers: list[logging.Handler] = []

    # Build stream handler if requested
    if log_to_stream:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(log_level)
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(ContextFilter())
        stream_handler.addFilter(SecretScrubbingFilter())
        handlers.append(stream_handler)

    # Build rotating file handler if requested (defaults to resolved_settings.log_to_file)
    should_log_to_file = log_to_file if log_to_file is not None else resolved_settings.log_to_file
    if should_log_to_file:
        target_path = Path(file_path or resolved_settings.log_file_path)
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                str(target_path),
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(JSONFormatter())
            file_handler.addFilter(ContextFilter())
            file_handler.addFilter(SecretScrubbingFilter())
            handlers.append(file_handler)
        except OSError as exc:
            logging.getLogger().warning(
                "Failed to initialize file logger at %s: %s", target_path, exc
            )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove previous handlers to guarantee idempotency
    for existing in list(root_logger.handlers):
        root_logger.removeHandler(existing)
    for h in handlers:
        root_logger.addHandler(h)

    # Configure application loggers
    for logger_name in ("goalcoach", "apps.api"):
        app_logger = logging.getLogger(logger_name)
        app_logger.setLevel(log_level)
        app_logger.propagate = True

    # Initialize isolated asynchronous sinks for backend, telemetry, and cost accounting
    from goalcoach.infrastructure.logging.sinks import setup_isolated_sinks

    setup_isolated_sinks(resolved_settings)

    # Quiet external loggers that would duplicate or clutter
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(log_level)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    _CONFIGURED = True


__all__ = ["configure_logging"]
