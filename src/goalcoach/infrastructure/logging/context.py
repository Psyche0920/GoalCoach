"""Task-local execution context management via Python contextvars."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any
from uuid import uuid4

_trace_id: ContextVar[str | None] = ContextVar("goalcoach_trace_id", default=None)
_request_id: ContextVar[str | None] = ContextVar("goalcoach_request_id", default=None)
_learner_id: ContextVar[str | None] = ContextVar("goalcoach_learner_id", default=None)
_session_id: ContextVar[str | None] = ContextVar("goalcoach_session_id", default=None)
_concept_id: ContextVar[str | None] = ContextVar("goalcoach_concept_id", default=None)

_KNOWN_CONTEXT_VARS: dict[str, ContextVar[str | None]] = {
    "trace_id": _trace_id,
    "request_id": _request_id,
    "learner_id": _learner_id,
    "session_id": _session_id,
    "concept_id": _concept_id,
}


def bind_context(**kwargs: Any) -> dict[str, Token[str | None]]:
    """Bind arbitrary context attributes to the current asynchronous task.

    Returns a mapping of variable name to the reset Token.
    """
    tokens: dict[str, Token[str | None]] = {}
    for key, value in kwargs.items():
        var = _KNOWN_CONTEXT_VARS.get(key)
        if var is not None:
            tokens[key] = var.set(str(value) if value is not None else None)
    return tokens


def reset_context(tokens: dict[str, Token[str | None]]) -> None:
    """Restore context variables using tokens from a previous bind_context call."""
    for key, token in tokens.items():
        var = _KNOWN_CONTEXT_VARS.get(key)
        if var is not None:
            var.reset(token)


def get_context() -> dict[str, str]:
    """Return a dictionary of all active, non-null context variables."""
    result: dict[str, str] = {}
    for key, var in _KNOWN_CONTEXT_VARS.items():
        val = var.get()
        if val is not None:
            result[key] = val
    return result


def clear_context() -> None:
    """Clear all context variables to None."""
    for var in _KNOWN_CONTEXT_VARS.values():
        var.set(None)


def bind_request_id(request_id: str) -> Token[str | None]:
    """Bind an API correlation ID to the current asynchronous request context."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the previous correlation context."""
    _request_id.reset(token)


def current_request_id() -> str:
    """Return the active request ID, or generate a random UUID if unconfigured."""
    return _request_id.get() or str(uuid4())


@contextmanager
def set_context(**kwargs: Any) -> Iterator[dict[str, str]]:
    """Context manager for temporary context binding in coroutines or tests."""
    tokens = bind_context(**kwargs)
    try:
        yield get_context()
    finally:
        reset_context(tokens)


__all__ = [
    "bind_context",
    "bind_request_id",
    "clear_context",
    "current_request_id",
    "get_context",
    "reset_context",
    "reset_request_id",
    "set_context",
]
