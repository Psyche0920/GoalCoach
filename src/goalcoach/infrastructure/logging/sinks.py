"""Isolated asynchronous logging sinks with non-blocking QueueHandler and immediate disk flushing."""

from __future__ import annotations

import atexit
import logging
import queue
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

from goalcoach.infrastructure.logging.filters import ContextFilter, SecretScrubbingFilter
from goalcoach.infrastructure.logging.formatters import NDJSONFormatter

if TYPE_CHECKING:
    from goalcoach.infrastructure.config import Settings

BACKEND_LOGGER_NAME = "goalcoach.backend"
TELEMETRY_LOGGER_NAME = "goalcoach.agent.telemetry"
COST_LOGGER_NAME = "goalcoach.agent.cost"

_GLOBAL_QUEUE: queue.Queue[logging.LogRecord] | None = None
_GLOBAL_LISTENER: QueueListener | None = None
_SINKS_INITIALIZED = False


class FlushingRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that immediately flushes records to disk.

    Prevents daemon processes (e.g. Uvicorn web servers) from holding log records
    in OS buffers indefinitely.
    """

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def _create_flushing_handler(
    target_path: str | Path,
    level: int,
    formatter: logging.Formatter,
) -> FlushingRotatingFileHandler:
    p = Path(target_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    handler = FlushingRotatingFileHandler(
        str(p),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.addFilter(ContextFilter())
    handler.addFilter(SecretScrubbingFilter())
    return handler


def setup_isolated_sinks(
    settings: Settings | None = None,
) -> tuple[logging.Logger, logging.Logger, logging.Logger]:
    """Configure physical sinks for backend, agent telemetry, and cost accounting.

    Guarantees strict isolation:
    - goalcoach.backend: captures general backend operational logs.
    - goalcoach.agent.telemetry: captures agent spans & tool latencies (propagate=False).
    - goalcoach.agent.cost: captures token metrics & USD accounting (propagate=False).
    """
    global _GLOBAL_LISTENER, _GLOBAL_QUEUE, _SINKS_INITIALIZED

    from goalcoach.infrastructure.config import Settings as ConfigSettings

    resolved_settings = settings or ConfigSettings()

    # Determine log level
    level_name = resolved_settings.log_level.upper()
    log_level = getattr(logging, level_name, logging.INFO)

    # Resolve paths relative to project root
    backend_path = resolved_settings.resolve_log_path(resolved_settings.backend_log_path)
    telemetry_path = resolved_settings.resolve_log_path(resolved_settings.agent_telemetry_log_path)
    cost_path = resolved_settings.resolve_log_path(resolved_settings.cost_accounting_log_path)

    formatter = NDJSONFormatter()

    # Create target file handlers
    backend_file_handler = _create_flushing_handler(backend_path, log_level, formatter)
    telemetry_file_handler = _create_flushing_handler(telemetry_path, logging.INFO, formatter)
    cost_file_handler = _create_flushing_handler(cost_path, logging.INFO, formatter)

    # Initialize queue and listener if not already active
    if _GLOBAL_LISTENER is not None:
        try:
            _GLOBAL_LISTENER.stop()
        except Exception:  # noqa: BLE001, S110
            pass

    _GLOBAL_QUEUE = queue.Queue(maxsize=resolved_settings.async_logging_queue_size)

    # Dedicated loggers
    backend_logger = logging.getLogger(BACKEND_LOGGER_NAME)
    backend_logger.setLevel(log_level)
    backend_logger.propagate = False  # Avoid double-dispatch to goalcoach ancestor

    telemetry_logger = logging.getLogger(TELEMETRY_LOGGER_NAME)
    telemetry_logger.setLevel(logging.INFO)
    telemetry_logger.propagate = False  # Strictly isolated

    cost_logger = logging.getLogger(COST_LOGGER_NAME)
    cost_logger.setLevel(logging.INFO)
    cost_logger.propagate = False  # Strictly isolated

    app_logger = logging.getLogger("goalcoach")
    api_logger = logging.getLogger("apps.api")

    # Clear prior QueueHandlers to guarantee idempotency across multiple setups
    for lgr in (backend_logger, telemetry_logger, cost_logger, app_logger, api_logger):
        for h in list(lgr.handlers):
            if isinstance(h, QueueHandler):
                lgr.removeHandler(h)

    # Attach QueueHandlers to telemetry and cost loggers
    telemetry_queue = queue.Queue(maxsize=resolved_settings.async_logging_queue_size)
    cost_queue = queue.Queue(maxsize=resolved_settings.async_logging_queue_size)
    backend_queue = queue.Queue(maxsize=resolved_settings.async_logging_queue_size)

    backend_handler = QueueHandler(backend_queue)
    backend_handler.addFilter(ContextFilter())
    backend_logger.addHandler(backend_handler)
    app_logger.addHandler(backend_handler)
    api_logger.addHandler(backend_handler)

    telemetry_logger.addHandler(QueueHandler(telemetry_queue))
    cost_logger.addHandler(QueueHandler(cost_queue))

    # Create queue listeners mapping queues to their dedicated file handlers
    listeners = [
        QueueListener(backend_queue, backend_file_handler, respect_handler_level=True),
        QueueListener(telemetry_queue, telemetry_file_handler, respect_handler_level=True),
        QueueListener(cost_queue, cost_file_handler, respect_handler_level=True),
    ]

    for listener in listeners:
        listener.start()

    class CompoundListener:
        def __init__(self, active_listeners: list[QueueListener]) -> None:
            self._listeners = active_listeners
            self._started = True

        def start(self) -> None:
            if self._started:
                return
            for lis in self._listeners:
                try:
                    lis.start()
                except Exception:  # noqa: BLE001, S110
                    pass
            self._started = True

        def stop(self) -> None:
            if not self._started:
                return
            for lis in self._listeners:
                try:
                    lis.stop()
                except Exception:  # noqa: BLE001, S110
                    pass
            self._started = False

    _GLOBAL_LISTENER = CompoundListener(listeners)  # type: ignore[assignment]
    _SINKS_INITIALIZED = True

    return backend_logger, telemetry_logger, cost_logger


def start_logging_queue() -> None:
    """Start background logging queue listener(s)."""
    if _GLOBAL_LISTENER is not None:
        _GLOBAL_LISTENER.start()


def stop_logging_queue() -> None:
    """Stop background logging queue listener(s) and flush all pending records."""
    if _GLOBAL_LISTENER is not None:
        _GLOBAL_LISTENER.stop()


# Automatically stop and flush upon process exit
atexit.register(stop_logging_queue)


def get_backend_logger() -> logging.Logger:
    """Return the dedicated backend operational logger."""
    return logging.getLogger(BACKEND_LOGGER_NAME)


def get_telemetry_logger() -> logging.Logger:
    """Return the isolated agent telemetry logger."""
    return logging.getLogger(TELEMETRY_LOGGER_NAME)


def get_cost_logger() -> logging.Logger:
    """Return the isolated cost accounting logger."""
    return logging.getLogger(COST_LOGGER_NAME)


__all__ = [
    "BACKEND_LOGGER_NAME",
    "COST_LOGGER_NAME",
    "TELEMETRY_LOGGER_NAME",
    "FlushingRotatingFileHandler",
    "get_backend_logger",
    "get_cost_logger",
    "get_telemetry_logger",
    "setup_isolated_sinks",
    "start_logging_queue",
    "stop_logging_queue",
]
