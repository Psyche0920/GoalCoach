"""Exercise provider envelopes and heterogeneous output through the real SDK/agent."""

import json
import logging

import httpx
import pytest
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from goalcoach.infrastructure.llm.pydantic_ai_models import CompletionResponseGuard, _TransientRetry
from goalcoach.infrastructure.llm.structured_output import structured_output


class SampleOutput(BaseModel):
    values: list[int] = Field(min_length=1)


@pytest.mark.asyncio
@pytest.mark.parametrize("as_tool", [False, True])
async def test_real_agent_tools_and_validator_survive_both_output_formats(as_tool: bool) -> None:
    calls = 0
    validations = 0
    tool_executions = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(parts=[ToolCallPart("curriculum", {}, "lookup")])
        data = {"values": "[1, 2]"}
        if as_tool:
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, data)])
        return ModelResponse(
            parts=[TextPart("Here is the result:\n```json\n" + json.dumps(data) + "\n```")]
        )

    agent = Agent(FunctionModel(model), output_type=structured_output(SampleOutput))

    @agent.tool_plain
    def curriculum() -> str:
        nonlocal tool_executions
        tool_executions += 1
        return "Valid IDs: 1, 2"

    @agent.output_validator
    def validate(result: SampleOutput) -> SampleOutput:
        nonlocal validations
        validations += 1
        return result

    result = await agent.run("Choose valid IDs")
    assert result.output.values == [1, 2]
    assert tool_executions == validations == 1
    assert calls == 2


@pytest.mark.asyncio
async def test_text_validation_retries_inside_agent_without_skipping_business_rules() -> None:
    calls = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        return ModelResponse(
            parts=[TextPart('{"values": [99]}' if calls == 1 else '{"values": [1]}')]
        )

    agent = Agent(
        FunctionModel(model), output_type=structured_output(SampleOutput), output_retries=1
    )

    @agent.output_validator
    def validate(result: SampleOutput) -> SampleOutput:
        if result.values != [1]:
            raise ModelRetry("Unknown curriculum ID")
        return result

    assert (await agent.run("Choose an ID")).output.values == [1]
    assert calls == 2
    assert not _TransientRetry(2).should_retry(UnexpectedModelBehavior("Invalid output"))


@pytest.mark.asyncio
async def test_incomplete_text_is_rejected() -> None:
    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart('{"values": [1')])

    agent = Agent(
        FunctionModel(model), output_type=structured_output(SampleOutput), output_retries=0
    )
    with pytest.raises(UnexpectedModelBehavior):
        await agent.run("Choose an ID")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected_status", "reason"),
    [
        ({"error": {"code": 401, "message": "private provider error"}}, 401, "provider_error"),
        ({"error": {"code": 429}}, 429, "provider_error"),
        ({"choices": None, "model": None, "object": None}, 502, "missing_choices"),
        ({"choices": [], "model": "test", "object": "chat.completion"}, 502, "missing_choices"),
        (
            {
                "choices": [{"message": {"content": None}}],
                "model": "test",
                "object": "chat.completion",
            },
            502,
            "empty_completion",
        ),
    ],
)
async def test_http_200_error_is_classified_by_real_sdk(
    payload: dict[str, object], expected_status: int, reason: str, caplog: pytest.LogCaptureFixture
) -> None:
    async def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond),
        event_hooks={"response": [CompletionResponseGuard().inspect]},
    ) as http_client:
        client = AsyncOpenAI(
            base_url="https://provider.test/v1",
            api_key="test",
            http_client=http_client,
            max_retries=0,
        )
        model = OpenAIChatModel("test", provider=OpenAIProvider(openai_client=client))
        with caplog.at_level(logging.WARNING), pytest.raises(ModelHTTPError) as captured:
            await Agent(model).run("private learner input")
        assert captured.value.status_code == expected_status
    assert reason in caplog.text
    assert "private provider error" not in caplog.text
    assert "private learner input" not in caplog.text
    assert _TransientRetry(2).should_retry(captured.value) == (expected_status != 401)


@pytest.mark.asyncio
async def test_valid_completion_is_preserved() -> None:
    payload = {
        "id": "test",
        "created": 0,
        "model": "test",
        "object": "chat.completion",
        "choices": [
            {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}
        ],
    }

    async def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond),
        event_hooks={"response": [CompletionResponseGuard().inspect]},
    ) as http_client:
        client = AsyncOpenAI(
            base_url="https://provider.test/v1",
            api_key="test",
            http_client=http_client,
            max_retries=0,
        )
        model = OpenAIChatModel("test", provider=OpenAIProvider(openai_client=client))
        assert (await Agent(model).run("test")).output == "ok"


@pytest.mark.parametrize("mode", ["auto", "tool", "text"])
def test_output_modes_are_explicit(mode: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic_ai import TextOutput, ToolOutput

    from goalcoach.infrastructure.llm.structured_output import output_instructions

    monkeypatch.setenv("GOALCOACH_LLM_OUTPUT_MODE", mode)
    outputs = structured_output(SampleOutput)
    assert any(isinstance(output, TextOutput) for output in outputs) == (mode != "tool")
    assert any(isinstance(output, ToolOutput) for output in outputs) == (mode != "text")
    if mode == "text":
        assert '"values"' in output_instructions(SampleOutput)


@pytest.mark.asyncio
async def test_request_client_closes_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from goalcoach.infrastructure.llm.pydantic_ai_models import (
        LLMUnavailableError,
        run_with_fallback,
    )

    monkeypatch.setenv("GOALCOACH_OFFLINE_LLM_FALLBACK", "false")
    monkeypatch.setenv("GOALCOACH_ENABLE_OLLAMA_FALLBACK", "false")
    client = AsyncOpenAI(base_url="https://provider.test/v1", api_key="test")
    model = OpenAIChatModel("test", provider=OpenAIProvider(openai_client=client))
    monkeypatch.setattr(
        "goalcoach.infrastructure.llm.pydantic_ai_models.get_openrouter_model", lambda: model
    )

    class FailingAgent:
        async def run(self, *args: object, **kwargs: object) -> None:
            raise UnexpectedModelBehavior("Invalid output")

    with pytest.raises(LLMUnavailableError):
        await run_with_fallback(FailingAgent(), "test")
    assert client.is_closed()


def test_wrapped_transport_failure_keeps_bounded_retry() -> None:
    from pydantic_ai.exceptions import ModelAPIError

    error = ModelAPIError(model_name="test", message="Connection error")
    error.__cause__ = httpx.ConnectError("Connection failed")
    retry = _TransientRetry(1)
    assert retry.should_retry(error)
    assert not retry.should_retry(error)


@pytest.mark.asyncio
async def test_diagnostics_measure_complete_body_and_hide_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import asyncio

    from goalcoach.infrastructure.llm.pydantic_ai_models import CompletionDiagnostics

    payload = {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "content": "PRIVATE RESPONSE",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "get_curriculum_catalog",
                                "arguments": "PRIVATE ARGUMENTS",
                            }
                        },
                        {"function": {"name": "PRIVATE UNKNOWN TOOL"}},
                    ],
                },
            }
        ],
    }
    body = json.dumps(payload).encode()

    class DelayedBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            await asyncio.sleep(0.01)
            yield body

    diagnostics = CompletionDiagnostics("planning_agent", "safe-request-id")
    request = httpx.Request(
        "POST",
        "https://provider.test/v1/chat/completions",
        json={
            "messages": [{"content": "PRIVATE PROMPT"}],
            "tools": [{"type": "function", "function": {"name": "get_curriculum_catalog"}}],
        },
        headers={"Authorization": "Bearer PRIVATE KEY"},
    )
    await diagnostics.request(request)
    response = httpx.Response(200, request=request, stream=DelayedBody())
    with caplog.at_level(logging.INFO):
        await diagnostics.response(response)
        diagnostics.finish()
    record = next(
        record
        for record in caplog.records
        if getattr(record, "extra", {}).get("event") == "llm_http_attempt"
    )
    fields = record.extra
    assert fields["duration_ms"] >= fields["headers_ms"] + 8
    assert fields["response_bytes"] == len(body)
    assert fields["tool_calls"] == ("get_curriculum_catalog", "unknown_tool")
    assert fields["finish_reasons"] == ("tool_calls",)
    assert response.content == body
    assert diagnostics.request_count == diagnostics.response_count == 1
    assert "PRIVATE" not in caplog.text
    assert "PRIVATE" not in repr(fields)


@pytest.mark.asyncio
async def test_parallel_diagnostic_contexts_are_isolated(caplog: pytest.LogCaptureFixture) -> None:
    import asyncio

    from goalcoach.infrastructure.llm.pydantic_ai_models import (
        CompletionDiagnostics,
        _completion_diagnostics,
        _diagnose_request,
        _diagnose_response,
    )

    async def invoke(component: str, count: int) -> CompletionDiagnostics:
        diagnostics = CompletionDiagnostics(component, component)
        token = _completion_diagnostics.set(diagnostics)
        try:
            for _ in range(count):
                request = httpx.Request(
                    "POST", "https://provider.test/v1/chat/completions", json={}
                )
                await _diagnose_request(request)
                await asyncio.sleep(0)
                await _diagnose_response(httpx.Response(200, request=request, json={}))
            diagnostics.finish()
            return diagnostics
        finally:
            _completion_diagnostics.reset(token)

    with caplog.at_level(logging.INFO):
        first, second = await asyncio.gather(invoke("planner", 2), invoke("teacher", 1))
    assert first.request_count == first.response_count == 2
    assert second.request_count == second.response_count == 1
    assert _completion_diagnostics.get() is None
    attempts = [
        record.extra
        for record in caplog.records
        if getattr(record, "extra", {}).get("event") == "llm_http_attempt"
    ]
    assert [(r["component"], r["model_request_number"]) for r in attempts] == [
        ("planner", 1),
        ("teacher", 1),
        ("planner", 2),
    ]
