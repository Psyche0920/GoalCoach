"""Normalize model formatting while retaining typed output and agent validators."""

from __future__ import annotations

import json
from typing import Generic, TypeVar, cast

from pydantic import BaseModel, ValidationError, create_model, model_validator
from pydantic_ai import ModelRetry, TextOutput, ToolOutput

from goalcoach.infrastructure.config import Settings
from goalcoach.infrastructure.llm.json_sanitizer import (
    extract_and_sanitize_json,
    normalize_json_value,
)

OutputT = TypeVar("OutputT", bound=BaseModel)


class StructuredOutputParser(Generic[OutputT]):
    """Convert model text to the same contract used by output tools."""

    def __init__(self, output_type: type[OutputT]) -> None:
        self.output_type = output_type

    def parse(self, text: str) -> OutputT:
        try:
            return self.output_type.model_validate(extract_and_sanitize_json(text))
        except ValidationError as exc:
            details = "; ".join(
                f"{'.'.join(str(part) for part in error['loc'])}: {error['type']}"
                for error in exc.errors(include_input=False, include_url=False)
            )
            raise ModelRetry(
                f"Return JSON matching the output schema. Invalid fields: {details}"
            ) from exc
        except (ValueError, TypeError) as exc:
            raise ModelRetry("Return one complete JSON object matching the output schema.") from exc


def structured_output(
    output_type: type[OutputT], *, name: str | None = None, description: str | None = None
) -> list[ToolOutput[OutputT] | TextOutput[OutputT]]:
    """Allow tool and text responses without replacing the agent's tool execution."""
    parser = StructuredOutputParser(output_type)
    text = TextOutput(parser.parse)
    # A model subclass preserves the original flat output-tool schema. Annotated
    # model types are wrapped in a `response` field by PydanticAI.
    normalized_type = cast(
        type[OutputT],
        create_model(
            output_type.__name__,
            __base__=output_type,
            __validators__={
                "normalize_format": model_validator(mode="before")(normalize_json_value)
            },
        ),
    )
    tool = ToolOutput(
        normalized_type,
        name=name,
        description=description,
    )
    mode = Settings().llm_output_mode
    if mode == "text":
        return [text]
    if mode == "tool":
        return [tool]
    return [tool, text]


def output_instructions(output_type: type[BaseModel]) -> str:
    """Give text-only models the schema normally supplied by the output tool."""
    instruction = "\nReturn the final result using an output tool or one complete JSON object matching its schema."
    if Settings().llm_output_mode == "text":
        instruction = "\nReturn one complete JSON object matching this schema: " + json.dumps(
            output_type.model_json_schema()
        )
    return instruction
