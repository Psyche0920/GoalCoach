"""Validated, immutable contracts for material production."""

from __future__ import annotations

import hashlib
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=12000)]
Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}$")]


class Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    def digest(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class MaterialsError(RuntimeError):
    """Base operational failure; messages must not contain source bodies or secrets."""


class GateError(MaterialsError):
    """A quality, evidence, or authorization gate failed."""


class StorageError(MaterialsError):
    """Persistent state could not be read or changed safely."""


class AgentError(MaterialsError):
    """An agent failed to provide a valid response."""


class Role(StrEnum):
    RESEARCH = "source_research"
    EVIDENCE = "evidence_cleaning"
    DESIGN = "curriculum_design"
    AUTHOR = "material_authoring"
    KNOWLEDGE = "knowledge_review"
    TEACHING = "teaching_review"
    ARBITER = "dispute_arbitration"
    CATALOG = "release_cataloging"


class Source(Record):
    source_id: Identifier
    title: Text
    category: Literal["official_standard", "textbook", "professional_social", "general_social"]
    publisher: Text
    edition: Text
    url: str = ""
    rights_evidence: Text
    allowed_uses: tuple[Literal["analysis", "adaptation", "redistribution"], ...]
    approved_by: Text
    status: Literal["approved", "revoked"] = "approved"

    def require(self, use: str) -> None:
        if self.status != "approved" or use not in self.allowed_uses:
            raise GateError(f"Source {self.source_id} does not permit {use}.")


class Span(Record):
    span_id: Identifier
    source_id: Identifier
    locator: Text
    text: Text
    source_hash: Text


class Evidence(Record):
    spans: tuple[Span, ...] = Field(min_length=1, max_length=100)


class Claim(Record):
    claim_id: Identifier
    statement: Text
    span_ids: tuple[Identifier, ...] = Field(min_length=1)
    scope: Text


class Claims(Record):
    claims: tuple[Claim, ...] = Field(min_length=1, max_length=40)


class Brief(Record):
    concept_id: Identifier
    objective: Text
    framework: Text
    hsk_level: int = Field(ge=1, le=6)
    prerequisite_ids: tuple[Identifier, ...] = ()


class SourcePlan(Record):
    selected_source_ids: tuple[Identifier, ...] = Field(min_length=1)
    rationale: Text
    missing_evidence: tuple[Text, ...] = ()


class Blueprint(Record):
    objective: Text
    vocabulary: tuple[Text, ...]
    grammar: tuple[Text, ...]
    teaching_notes: Text
    claim_ids: tuple[Identifier, ...] = Field(min_length=1)


class Card(Record):
    item_id: Identifier
    card_type: Literal["goal", "vocab", "grammar", "example", "tip", "mini_dialogue"]
    text_zh: Text
    pinyin: Text
    meaning_en: Text
    explanation_en: Text
    claim_ids: tuple[Identifier, ...] = Field(min_length=1)
    origin: Literal["original", "adapted", "quoted"] = "original"


class Exercise(Record):
    exercise_id: Identifier
    exercise_type: Literal[
        "meaning_mcq",
        "zh_to_en_mcq",
        "en_to_zh_mcq",
        "fill_blank",
        "reorder",
        "translate_to_zh",
        "dialogue_choice",
    ]
    prompt: Text
    instruction: Text
    options: tuple[Text, ...] = ()
    answer: Text
    accepted_answers: tuple[Text, ...] = ()
    explanation: Text
    error_tags: tuple[Text, ...] = ()
    claim_ids: tuple[Identifier, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def check_answers(self) -> Self:
        if self.exercise_type.endswith("mcq") or self.exercise_type == "dialogue_choice":
            if len(set(self.options)) < 2 or len(set(self.options)) != len(self.options):
                raise ValueError("Multiple-choice exercises require distinct options.")
            if self.answer not in self.options:
                raise ValueError("The answer must be an option's exact text.")
        return self


class Material(Record):
    title_zh: Text
    title_en: Text
    estimated_minutes: int = Field(ge=1, le=120)
    cards: tuple[Card, ...] = Field(min_length=1, max_length=12)
    exercises: tuple[Exercise, ...] = Field(min_length=1, max_length=12)
    teacher_notes: Text

    @model_validator(mode="after")
    def unique_items(self) -> Self:
        ids = [x.item_id for x in self.cards] + [x.exercise_id for x in self.exercises]
        if len(ids) != len(set(ids)):
            raise ValueError("Material item IDs must be unique.")
        return self


class Issue(Record):
    location: Text
    severity: Literal["blocking", "minor"]
    finding: Text
    evidence_span_ids: tuple[Identifier, ...] = ()


class Review(Record):
    verdict: Literal["pass", "revise", "dispute"]
    accuracy: int = Field(ge=0, le=5)
    teachability: int = Field(ge=0, le=5)
    evidence: int = Field(ge=0, le=5)
    difficulty: int = Field(ge=0, le=5)
    naturalness: int = Field(ge=0, le=5)
    issues: tuple[Issue, ...]
    rationale: Text

    @property
    def score(self) -> float:
        return sum(a * b / 5 for a, b in zip(self.dimensions, (30, 25, 20, 15, 10), strict=True))

    @property
    def dimensions(self) -> tuple[int, ...]:
        return self.accuracy, self.teachability, self.evidence, self.difficulty, self.naturalness

    @property
    def passes(self) -> bool:
        return (
            self.verdict == "pass"
            and min(self.dimensions) >= 3
            and self.score >= 85
            and not any(i.severity == "blocking" for i in self.issues)
        )


class Solution(Record):
    exercise_id: Identifier
    answer: Text
    rationale: Text


class Solutions(Record):
    solutions: tuple[Solution, ...]


class Decision(Record):
    decision: Literal["revise", "exclude", "needs_human"]
    rationale: Text
    evidence_span_ids: tuple[Identifier, ...]
    revision_instructions: Text


class Catalog(Record):
    summary: Text
    tags: tuple[Text, ...]


class Packet(Record):
    brief: Brief
    sources: tuple[Source, ...]
    evidence: Evidence
    claims: Claims
    blueprint: Blueprint
    material: Material
    knowledge_review: Review
    teaching_review: Review
    catalog: Catalog

    @property
    def quality_passes(self) -> bool:
        reviews = (self.knowledge_review, self.teaching_review)
        conservative = tuple(
            min(values) for values in zip(*(r.dimensions for r in reviews), strict=True)
        )
        score = sum(
            value * weight / 5
            for value, weight in zip(conservative, (30, 25, 20, 15, 10), strict=True)
        )
        return all(r.passes for r in reviews) and score >= 85


class UsageRecord(Record):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost_usd: Decimal | None = Field(default=None, ge=0)
    model: Text


class UsageSummary(Record):
    attempts: int = Field(ge=0)
    measured_attempts: int = Field(ge=0)
    priced_attempts: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    known_estimated_cost_usd: Decimal = Field(ge=0)


class RunSummary(Record):
    run_id: str
    state: str
    request_count: int


class VersionSummary(Record):
    version_id: str
    run_id: str
    state: str


class TaskSummary(Record):
    task_id: str
    role: str
    state: str
    result_json: str | None


class WorkflowResult(Record):
    run_id: str
    state: str
    version_id: str | None = None
    reason: str = ""
