"""
src/goalcoach/infrastructure/llm/pydantic_ai_models.py
PydanticAI model providers for hosted OpenRouter and local Ollama Gemma 4 fallback.
"""

from __future__ import annotations

import json
import logging
import re
from asyncio import sleep
from contextvars import ContextVar
from dataclasses import dataclass, field
from json import JSONDecodeError
from random import random
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

import httpx
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult

try:
    from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError, UnexpectedModelBehavior
except ImportError:
    from pydantic_ai.exceptions import ModelHTTPError as ModelAPIError  # type: ignore[no-redef]
    from pydantic_ai.exceptions import UnexpectedModelBehavior

    ModelHTTPError = ModelAPIError  # type: ignore[misc]

try:
    from pydantic_ai.models.openai import OpenAIChatModel as OpenAIModel
except ImportError:
    from pydantic_ai.models.openai import OpenAIModel  # type: ignore[assignment]
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider

from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.telemetry import (
    AgentTelemetryEvent,
    current_request_id,
    emit_agent_telemetry,
    token_usage,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _CompletionAttempt:
    sequence: int
    started_at: float
    tool_names: frozenset[str]


@dataclass(slots=True)
class CompletionDiagnostics:
    """Track HTTP attempts for one agent invocation without storing model content."""

    component: str
    request_id: str
    started_at: float = field(default_factory=perf_counter)
    request_count: int = 0
    response_count: int = 0

    async def request(self, request: httpx.Request) -> None:
        if not request.url.path.endswith("/chat/completions"):
            return
        self.request_count += 1
        tools: set[str] = set()
        try:
            payload = json.loads(request.content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("tools"), list):
            for tool in payload["tools"]:
                if not isinstance(tool, dict) or not isinstance(tool.get("function"), dict):
                    continue
                name = tool["function"].get("name")
                if isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", name):
                    tools.add(name)
        request.extensions["goalcoach_completion_attempt"] = _CompletionAttempt(
            self.request_count, perf_counter(), frozenset(tools)
        )

    async def response(self, response: httpx.Response) -> None:
        attempt = response.request.extensions.get("goalcoach_completion_attempt")
        if not isinstance(attempt, _CompletionAttempt):
            return
        headers_ms = round((perf_counter() - attempt.started_at) * 1000, 2)
        self.response_count += 1
        streamed = response.headers.get("content-type", "").startswith("text/event-stream")
        if streamed:
            self._emit(attempt, response.status_code, headers_ms, None, None, (), ())
            return
        try:
            await response.aread()
        except httpx.HTTPError:
            self._emit(attempt, response.status_code, headers_ms, None, None, (), ())
            raise
        finishes: list[str] = []
        calls: list[str] = []
        try:
            payload = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if isinstance(choices, list):
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                reason = choice.get("finish_reason")
                if isinstance(reason, str) and reason in {
                    "stop",
                    "length",
                    "tool_calls",
                    "content_filter",
                    "function_call",
                    "error",
                }:
                    finishes.append(reason)
                message = choice.get("message")
                tool_calls = message.get("tool_calls") if isinstance(message, dict) else None
                if isinstance(tool_calls, list):
                    for call in tool_calls:
                        function = call.get("function") if isinstance(call, dict) else None
                        name = function.get("name") if isinstance(function, dict) else None
                        calls.append(
                            name
                            if isinstance(name, str) and name in attempt.tool_names
                            else "unknown_tool"
                        )
        self._emit(
            attempt,
            response.status_code,
            headers_ms,
            round((perf_counter() - attempt.started_at) * 1000, 2),
            len(response.content),
            tuple(finishes),
            tuple(calls),
        )

    def _emit(
        self,
        attempt: _CompletionAttempt,
        status: int,
        headers_ms: float,
        duration_ms: float | None,
        response_bytes: int | None,
        finishes: tuple[str, ...],
        calls: tuple[str, ...],
    ) -> None:
        logger.info(
            "Model HTTP attempt: component=%s request=%d status=%d headers_ms=%.2f duration_ms=%s response_bytes=%s finish_reasons=%s tool_calls=%s",
            self.component,
            attempt.sequence,
            status,
            headers_ms,
            duration_ms,
            response_bytes,
            finishes,
            calls,
            extra={
                "extra": {
                    "event": "llm_http_attempt",
                    "component": self.component,
                    "request_id": self.request_id,
                    "model_request_number": attempt.sequence,
                    "status_code": status,
                    "headers_ms": headers_ms,
                    "duration_ms": duration_ms,
                    "response_bytes": response_bytes,
                    "finish_reasons": finishes,
                    "tool_calls": calls,
                }
            },
        )

    def finish(self) -> None:
        duration_ms = round((perf_counter() - self.started_at) * 1000, 2)
        logger.info(
            "Model HTTP summary: component=%s requests=%d responses=%d duration_ms=%.2f",
            self.component,
            self.request_count,
            self.response_count,
            duration_ms,
            extra={
                "extra": {
                    "event": "llm_http_summary",
                    "component": self.component,
                    "request_id": self.request_id,
                    "model_request_count": self.request_count,
                    "model_response_count": self.response_count,
                    "duration_ms": duration_ms,
                }
            },
        )


_completion_diagnostics: ContextVar[CompletionDiagnostics | None] = ContextVar(
    "goalcoach_completion_diagnostics", default=None
)


async def _diagnose_request(request: httpx.Request) -> None:
    diagnostics = _completion_diagnostics.get()
    if diagnostics is not None:
        await diagnostics.request(request)


async def _diagnose_response(response: httpx.Response) -> None:
    diagnostics = _completion_diagnostics.get()
    if diagnostics is not None:
        await diagnostics.response(response)


class CompletionResponseGuard:
    """Inspect non-streaming completions before SDK parsing without logging content."""

    async def inspect(self, response: httpx.Response) -> None:
        if not response.request.url.path.endswith("/chat/completions"):
            return
        if not response.is_success or response.headers.get("content-type", "").startswith(
            "text/event-stream"
        ):
            return
        await response.aread()
        try:
            payload = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._reject(response, "invalid_json")
            return
        if not isinstance(payload, dict):
            self._reject(response, "invalid_envelope")
            return
        if payload.get("error") is not None:
            error = payload["error"]
            code = error.get("code") if isinstance(error, dict) else None
            try:
                status = int(code)
            except (ValueError, TypeError):
                status = 502
            if not 400 <= status <= 599:
                status = 502
            self._reject(response, "provider_error", status)
            return
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            self._reject(response, "missing_choices")
            return
        if not isinstance(payload.get("model"), str) or payload.get("object") != "chat.completion":
            self._reject(response, "invalid_envelope")
            return
        for choice in choices:
            if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
                self._reject(response, "missing_message")
                return
            message = choice["message"]
            if not message.get("content") and not message.get("tool_calls"):
                self._reject(response, "empty_completion")
                return

    def _reject(self, response: httpx.Response, reason: str, error_code: int = 502) -> None:
        logger.warning(
            "Provider completion rejected: reason=%s http_status=%d error_code=%d",
            reason,
            response.status_code,
            error_code,
            extra={
                "extra": {
                    "event": "provider_response_rejected",
                    "reason": reason,
                    "status_code": response.status_code,
                    "error_code": error_code,
                }
            },
        )
        # Make the SDK classify an error envelope as a provider failure, even when
        # the upstream sends HTTP 200. Never synthesize completion data.
        response.status_code = error_code


class _TransientRetry:
    """Delay one bounded retry for provider faults that are often self-healing."""

    def __init__(self, max_retries: int) -> None:
        self.remaining = max_retries

    def should_retry(self, err: Exception) -> bool:
        # PydanticAI wraps SDK connection errors; retain their transport cause.
        cause: BaseException | None = err
        transport_failure = False
        seen: set[int] = set()
        while cause is not None and id(cause) not in seen:
            seen.add(id(cause))
            transport_failure = transport_failure or isinstance(cause, httpx.TransportError)
            cause = cause.__cause__
        transient = (
            isinstance(err, httpx.TransportError)
            or (
                isinstance(err, ModelHTTPError)
                and err.status_code in {408, 409, 425, 429, 500, 502, 503, 504}
            )
            or (isinstance(err, ModelAPIError) and transport_failure)
        )
        should_retry = transient and self.remaining > 0
        if should_retry:
            self.remaining -= 1
        return should_retry

    @property
    def delay_seconds(self) -> float:
        return 0.5 + random() * 0.5


class LLMUnavailableError(RuntimeError):
    """Raised when no configured LLM can complete an agent request."""


class AgentOutputError(RuntimeError):
    """Raised when a model response cannot satisfy deterministic domain guardrails."""


# Ensure backward compatibility for result.data -> result.output
if not hasattr(AgentRunResult, "data"):
    AgentRunResult.data = property(lambda self: getattr(self, "output", None))  # type: ignore[attr-defined]

# Ensure backward compatibility for Agent(..., result_type=...) -> output_type
_orig_agent_init = Agent.__init__


def _compat_agent_init(self: Any, *args: Any, **kwargs: Any) -> None:
    if "result_type" in kwargs:
        kwargs["output_type"] = kwargs.pop("result_type")
    _orig_agent_init(self, *args, **kwargs)


Agent.__init__ = _compat_agent_init  # type: ignore[method-assign]

try:
    from pydantic_ai.models.test import TestModel

    _orig_test_model_init = TestModel.__init__

    def _compat_test_model_init(self: Any, *args: Any, **kwargs: Any) -> None:
        if "custom_result_text" in kwargs:
            val = kwargs.pop("custom_result_text")
            try:
                import json

                kwargs["custom_output_args"] = json.loads(val)
            except JSONDecodeError:
                kwargs["custom_output_text"] = val
        _orig_test_model_init(self, *args, **kwargs)

    TestModel.__init__ = _compat_test_model_init  # type: ignore[method-assign]
except ImportError:
    pass


def get_openrouter_model() -> OpenAIModel:
    """Returns an OpenAIModel configured for OpenRouter."""
    settings = Settings()
    base_url = str(settings.llm_base_url or "https://openrouter.ai/api/v1")
    api_key = settings.llm_api_key or "unconfigured_key"
    model_name = settings.llm_model or "qwen/qwen-2.5-72b-instruct"
    http_client = httpx.AsyncClient(
        timeout=settings.llm_timeout_seconds,
        event_hooks={
            "request": [_diagnose_request],
            "response": [_diagnose_response, CompletionResponseGuard().inspect],
        },
    )
    client = AsyncOpenAI(base_url=base_url, api_key=api_key, http_client=http_client, max_retries=0)
    if urlparse(base_url).hostname == "openrouter.ai":
        return OpenRouterModel(model_name, provider=OpenRouterProvider(openai_client=client))
    return OpenAIModel(model_name=model_name, provider=OpenAIProvider(openai_client=client))


def get_ollama_fallback_model() -> OpenAIModel:
    """Returns an OpenAIModel configured for local Ollama Gemma 4 fallback."""
    settings = Settings()
    base_url = str(settings.fallback_llm_base_url or "http://localhost:11434/v1")
    model_name = settings.fallback_llm_model or "unsloth/gemma-4-12b-it-GGUF"
    http_client = httpx.AsyncClient(
        timeout=settings.llm_timeout_seconds,
        event_hooks={
            "request": [_diagnose_request],
            "response": [_diagnose_response, CompletionResponseGuard().inspect],
        },
    )
    client = AsyncOpenAI(
        base_url=base_url, api_key="ollama", http_client=http_client, max_retries=0
    )
    provider = OpenAIProvider(openai_client=client)
    return OpenAIModel(model_name=model_name, provider=provider)


async def run_with_fallback(
    agent: Any,
    prompt: str,
    deps: Any = None,
    *,
    component: str = "agent",
    prompt_version: str = "v1",
) -> tuple[Any, str]:
    """Own the primary client's lifecycle for one bounded agent run."""
    if Settings().offline_llm_fallback:
        raise LLMUnavailableError("Offline LLM fallback is enabled for deterministic execution")
    diagnostics = CompletionDiagnostics(component, current_request_id())
    token = _completion_diagnostics.set(diagnostics)
    try:
        model = get_openrouter_model()
        async with model.client:
            return await _run_with_fallback(
                model, agent, prompt, deps, component=component, prompt_version=prompt_version
            )
    finally:
        diagnostics.finish()
        _completion_diagnostics.reset(token)


async def _run_with_fallback(
    model: OpenAIModel,
    agent: Any,
    prompt: str,
    deps: Any = None,
    *,
    component: str = "agent",
    prompt_version: str = "v1",
) -> tuple[Any, str]:
    """Run the primary model and optionally use a configured local fallback."""
    settings = Settings()
    if settings.offline_llm_fallback:
        raise LLMUnavailableError("Offline LLM fallback is enabled for deterministic execution")
    primary_model = model
    request_id = current_request_id()
    started_at = perf_counter()
    primary_retries = _TransientRetry(settings.llm_max_retries)

    logger.debug(
        "Invoking model inference: component=%s provider=openrouter model=%s prompt_len=%d",
        component,
        primary_model.model_name,
        len(prompt),
        extra={
            "extra": {
                "event": "llm_inference_started",
                "component": component,
                "gen_ai.system": "openrouter",
                "gen_ai.request.model": primary_model.model_name,
                "prompt_length": len(prompt),
            }
        },
    )

    try:
        while True:
            try:
                result = await agent.run(
                    prompt,
                    deps=deps,
                    model=primary_model,
                )
                break
            except (httpx.HTTPError, ModelAPIError, UnexpectedModelBehavior) as err:
                if not primary_retries.should_retry(err):
                    raise
                logger.warning(
                    "Transient primary model %s failure (%s); retrying.",
                    "provider error"
                    if isinstance(err, ModelAPIError)
                    else "response or transport error",
                    type(err).__name__,
                )
                await sleep(primary_retries.delay_seconds)
        input_tokens, output_tokens = token_usage(result)
        emit_agent_telemetry(
            AgentTelemetryEvent(
                request_id=request_id,
                component=component,
                provider="openrouter",
                model=primary_model.model_name,
                prompt_version=prompt_version,
                latency_ms=round((perf_counter() - started_at) * 1000, 2),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=None,
                validation_succeeded=True,
                fallback_used=False,
            )
        )
        return result, f"openrouter:{primary_model.model_name}"
    except (httpx.HTTPError, ModelAPIError, UnexpectedModelBehavior) as err:
        failure_kind = (
            "output validation"
            if isinstance(err, UnexpectedModelBehavior)
            else "connection or provider"
        )
        if not settings.enable_ollama_fallback:
            emit_agent_telemetry(
                AgentTelemetryEvent(
                    request_id=request_id,
                    component=component,
                    provider="openrouter",
                    model=primary_model.model_name,
                    prompt_version=prompt_version,
                    latency_ms=round((perf_counter() - started_at) * 1000, 2),
                    input_tokens=None,
                    output_tokens=None,
                    estimated_cost_usd=None,
                    validation_succeeded=False,
                    fallback_used=False,
                    failure_kind=failure_kind,
                )
            )
            logger.warning(
                "Primary model %s failure (%s); Ollama fallback is disabled.",
                failure_kind,
                type(err).__name__,
            )
            raise LLMUnavailableError(
                f"LLM unavailable: primary request failed ({type(err).__name__})"
            ) from err

        logger.warning(
            "Primary model %s failure (%s); trying configured Ollama fallback.",
            failure_kind,
            type(err).__name__,
            extra={
                "extra": {
                    "event": "llm_fallback_engaged",
                    "primary_provider": "openrouter",
                    "primary_model": primary_model.model_name,
                    "failure_kind": failure_kind,
                    "fallback_provider": "ollama",
                }
            },
        )
        fallback_model = get_ollama_fallback_model()
        fallback_started_at = perf_counter()
        fallback_retries = _TransientRetry(min(settings.llm_max_retries, 1))
        try:
            while True:
                try:
                    result = await agent.run(
                        prompt,
                        deps=deps,
                        model=fallback_model,
                    )
                    break
                except (
                    httpx.HTTPError,
                    ModelAPIError,
                    UnexpectedModelBehavior,
                ) as fallback_attempt_err:
                    if not fallback_retries.should_retry(fallback_attempt_err):
                        raise
                    await sleep(fallback_retries.delay_seconds)
            input_tokens, output_tokens = token_usage(result)
            emit_agent_telemetry(
                AgentTelemetryEvent(
                    request_id=request_id,
                    component=component,
                    provider="ollama",
                    model=fallback_model.model_name,
                    prompt_version=prompt_version,
                    latency_ms=round((perf_counter() - fallback_started_at) * 1000, 2),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost_usd=None,
                    validation_succeeded=True,
                    fallback_used=True,
                )
            )
            return result, f"ollama:{fallback_model.model_name}"
        except (httpx.HTTPError, ModelAPIError, UnexpectedModelBehavior) as fallback_err:
            emit_agent_telemetry(
                AgentTelemetryEvent(
                    request_id=request_id,
                    component=component,
                    provider="ollama",
                    model=fallback_model.model_name,
                    prompt_version=prompt_version,
                    latency_ms=round((perf_counter() - fallback_started_at) * 1000, 2),
                    input_tokens=None,
                    output_tokens=None,
                    estimated_cost_usd=None,
                    validation_succeeded=False,
                    fallback_used=True,
                    failure_kind=(
                        "output validation"
                        if isinstance(fallback_err, UnexpectedModelBehavior)
                        else "connection or provider"
                    ),
                )
            )
            raise LLMUnavailableError(
                "LLM unavailable: primary and fallback model requests failed"
            ) from fallback_err
        finally:
            await fallback_model.client.close()


def get_output_retries() -> int:
    """Return the configured number of structured-output validation retries."""
    return Settings().llm_max_retries
