"""
src/goalcoach/infrastructure/llm/pydantic_ai_models.py
PydanticAI model providers for hosted OpenRouter and local Ollama Gemma 4 fallback.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
try:
    from pydantic_ai.models.openai import OpenAIChatModel as OpenAIModel
except ImportError:
    from pydantic_ai.models.openai import OpenAIModel  # type: ignore[assignment]
from pydantic_ai.providers.openai import OpenAIProvider

from goalcoach.infrastructure.config import Settings

logger = logging.getLogger(__name__)

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
            except Exception:
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
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIModel(model_name=model_name, provider=provider)


def get_ollama_fallback_model() -> OpenAIModel:
    """Returns an OpenAIModel configured for local Ollama Gemma 4 fallback."""
    settings = Settings()
    base_url = str(settings.fallback_llm_base_url or "http://localhost:11434/v1")
    model_name = settings.fallback_llm_model or "unsloth/gemma-4-12b-it-GGUF"
    provider = OpenAIProvider(base_url=base_url, api_key="ollama")
    return OpenAIModel(model_name=model_name, provider=provider)


async def run_with_fallback(agent: Any, prompt: str, deps: Any = None) -> tuple[Any, str]:
    """Executes a PydanticAI agent on OpenRouter; falls back to Ollama Gemma 4 on connection/timeout errors."""
    primary_model = get_openrouter_model()
    fallback_model = get_ollama_fallback_model()

    try:
        result = await agent.run(prompt, deps=deps, model=primary_model)
        return result, f"openrouter:{primary_model.model_name}"
    except (httpx.HTTPError, httpx.TimeoutException, Exception) as err:
        logger.warning("Primary model failed (%s). Falling back to local Ollama Gemma 4.", err)
        result = await agent.run(prompt, deps=deps, model=fallback_model)
        return result, f"ollama:{fallback_model.model_name}"
