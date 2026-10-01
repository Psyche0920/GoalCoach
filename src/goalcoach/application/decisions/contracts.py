"""Contracts for finite choices; arbitrary model prose cannot cross this boundary."""

from __future__ import annotations

from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

Probability = Annotated[float, Field(ge=0, le=1)]


class ChoiceQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["choice"] = "choice"
    instructions: str
    criteria: dict[str, str] = Field(min_length=2, max_length=255)


class ChoiceAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["choice"]
    choice: str
    confidence: Probability
    probabilities: dict[str, Probability]

    @model_validator(mode="after")
    def validate_distribution(self) -> ChoiceAnswer:
        if self.choice not in self.probabilities:
            raise ValueError("Selected option is missing from probabilities")
        if abs(sum(self.probabilities.values()) - 1) > 0.02:
            raise ValueError("Choice probabilities must sum to one")
        if self.probabilities[self.choice] + 0.001 < max(self.probabilities.values()):
            raise ValueError("Selected option must have maximal probability")
        return self


class DecisionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    state: str
    questions: dict[str, ChoiceQuestion] = Field(min_length=1)


class DecisionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    model: str
    answers: dict[str, ChoiceAnswer]


class DecisionError(RuntimeError):
    """A provider failed to return validated finite choices."""


class DecisionClient(Protocol):
    async def decide(self, request: DecisionRequest) -> DecisionResponse: ...
