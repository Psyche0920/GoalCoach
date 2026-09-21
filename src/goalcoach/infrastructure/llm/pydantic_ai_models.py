"""
src/goalcoach/infrastructure/llm/pydantic_ai_models.py
PydanticAI model providers for hosted OpenRouter and local Ollama Gemma 4 fallback.
"""

from __future__ import annotations

import logging
from json import JSONDecodeError
from typing import Any

import httpx
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior

try:
    from pydantic_ai.models.openai import OpenAIChatModel as OpenAIModel
except ImportError:
    from pydantic_ai.models.openai import OpenAIModel  # type: ignore[assignment]
from pydantic_ai.providers.openai import OpenAIProvider

from goalcoach.infrastructure.config import Settings

logger = logging.getLogger(__name__)


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
    http_client = httpx.AsyncClient(timeout=settings.llm_timeout_seconds)
    provider = OpenAIProvider(base_url=base_url, api_key=api_key, http_client=http_client)
    return OpenAIModel(model_name=model_name, provider=provider)


def get_ollama_fallback_model() -> OpenAIModel:
    """Returns an OpenAIModel configured for local Ollama Gemma 4 fallback."""
    settings = Settings()
    base_url = str(settings.fallback_llm_base_url or "http://localhost:11434/v1")
    model_name = settings.fallback_llm_model or "unsloth/gemma-4-12b-it-GGUF"
    http_client = httpx.AsyncClient(timeout=settings.llm_timeout_seconds)
    provider = OpenAIProvider(base_url=base_url, api_key="ollama", http_client=http_client)
    return OpenAIModel(model_name=model_name, provider=provider)


async def run_with_fallback(agent: Any, prompt: str, deps: Any = None) -> tuple[Any, str]:
    """Run the primary model and optionally use a configured local fallback."""
    settings = Settings()
    primary_model = get_openrouter_model()

    try:
        result = await agent.run(prompt, deps=deps, model=primary_model)
        return result, f"openrouter:{primary_model.model_name}"
    except (httpx.HTTPError, ModelAPIError, UnexpectedModelBehavior) as err:
        failure_kind = (
            "output validation"
            if isinstance(err, UnexpectedModelBehavior)
            else "connection or provider"
        )
        if not settings.enable_ollama_fallback:
            logger.warning(
                "Primary model %s failure (%s); Ollama fallback is disabled.",
                failure_kind,
                err,
            )
            raise LLMUnavailableError("LLM unavailable: primary model request failed") from err

        logger.warning(
            "Primary model %s failure (%s); trying configured Ollama fallback.",
            failure_kind,
            err,
        )
        fallback_model = get_ollama_fallback_model()
        try:
            result = await agent.run(prompt, deps=deps, model=fallback_model)
            return result, f"ollama:{fallback_model.model_name}"
        except (httpx.HTTPError, ModelAPIError, UnexpectedModelBehavior) as fallback_err:
            raise LLMUnavailableError(
                "LLM unavailable: primary and fallback model requests failed"
            ) from fallback_err


def get_output_retries() -> int:
    """Return the configured number of structured-output validation retries."""
    return Settings().llm_max_retries
