"""Bounded durable orchestration, independent review and evidence gates."""

from __future__ import annotations

import asyncio
import hashlib
from contextvars import ContextVar
from typing import TypeVar

from pydantic import Field

from goalcoach.materials.agents import AgentRunner, MeteredRunner
from goalcoach.materials.models import (
    Blueprint,
    Brief,
    Card,
    Catalog,
    Claims,
    Decision,
    Evidence,
    Exercise,
    GateError,
    Material,
    Packet,
    Record,
    Review,
    Role,
    Solutions,
    Source,
    SourcePlan,
    WorkflowResult,
)
from goalcoach.materials.store import Workbench

T = TypeVar("T", bound=Record)


class SourceList(Record):
    sources: tuple[Source, ...]


class BlindExercise(Record):
    exercise_id: str
    prompt: str
    instruction: str
    options: tuple[str, ...]


class BlindExam(Record):
    exercises: tuple[BlindExercise, ...]


class Feedback(Record):
    instructions: str


class RunInput(Record):
    brief: Brief
    sources: SourceList
    evidence: Evidence
    runner_identity: str
    max_revisions: int = Field(ge=0, le=2)


def validate_evidence(claims: Claims, evidence: Evidence, sources: tuple[Source, ...]) -> None:
    spans = {s.span_id: s for s in evidence.spans}
    source_map = {s.source_id: s for s in sources}
    if len(spans) != len(evidence.spans) or len(source_map) != len(sources):
        raise GateError("Duplicate evidence or source IDs.")
    if any(span.source_id not in source_map for span in evidence.spans):
        raise GateError("Evidence references an unregistered source.")
    ids = [c.claim_id for c in claims.claims]
    if len(ids) != len(set(ids)):
        raise GateError("Duplicate claim IDs.")
    for claim in claims.claims:
        if any(s not in spans for s in claim.span_ids):
            raise GateError("A claim references nonexistent evidence.")
    if not any(
        source_map[spans[s].source_id].category in {"official_standard", "textbook"}
        for c in claims.claims
        for s in c.span_ids
    ):
        raise GateError("A unit needs formal teaching evidence, not only social usage.")


def validate_material(material: Material, claims: Claims) -> None:
    valid = {c.claim_id for c in claims.claims}
    items: tuple[Card | Exercise, ...] = (*material.cards, *material.exercises)
    for item in items:
        if any(cid not in valid for cid in item.claim_ids):
            raise GateError("Material references nonexistent claims.")


class ProductionWorkflow:
    def __init__(
        self, store: Workbench, runner: AgentRunner, request_limit: int = 30, max_revisions: int = 2
    ) -> None:
        self.store = store
        self.runner = runner
        self.request_limit = request_limit
        self.max_revisions = max_revisions
        self._run_owner: ContextVar[str | None] = ContextVar("materials_run_owner", default=None)

    async def step(self, run_id: str, role: Role, output: type[T], inputs: tuple[Record, ...]) -> T:
        run_owner = self._run_owner.get()
        if run_owner is not None:
            self.store.renew_run(run_id, run_owner)
        key = hashlib.sha256(
            f"{run_id}:{self.runner.identity}:{role}:{output.__name__}:{':'.join(x.digest() for x in inputs)}".encode()
        ).hexdigest()
        cached = self.store.cached(key, output)
        if cached is not None:
            return cached
        owner = self.store.claim_task(key, run_id, role.value, self.request_limit)
        usage = None
        try:
            if isinstance(self.runner, MeteredRunner):
                measured = await self.runner.run_metered(role, output, inputs)
                result, usage = measured.output, measured.usage
            else:
                result = await self.runner.run(role, output, inputs)
        except BaseException:
            self.store.finish_task(key, owner, None)
            raise
        self.store.finish_task(key, owner, result, usage)
        return result

    async def run(
        self, brief: Brief, source_ids: tuple[str, ...], resume: str | None = None
    ) -> WorkflowResult:
        if not source_ids or len(source_ids) != len(set(source_ids)):
            raise GateError("Select one or more distinct source IDs.")
        sources = tuple(self.store.source(sid) for sid in source_ids)
        for source in sources:
            source.require("analysis")
            source.require("adaptation")
        spans = tuple(s for s in self.store.spans() if s.source_id in source_ids)
        if not spans:
            raise GateError("Import source documents before generating materials.")
        if len(spans) > 100:
            raise GateError(
                "Selected sources contain more than 100 evidence spans; import a focused chapter or select fewer sources."
            )
        evidence = Evidence(spans=spans)
        run_input = RunInput(
            brief=brief,
            sources=SourceList(sources=sources),
            evidence=evidence,
            runner_identity=self.runner.identity,
            max_revisions=self.max_revisions,
        )
        run_id = self.store.start(run_input.digest(), resume)
        owner = self.store.acquire_run(run_id)
        token = self._run_owner.set(owner)
        try:
            return await self._produce(run_id, run_input)
        except BaseException:
            self.store.state(run_id, "interrupted", owner)
            raise
        finally:
            self._run_owner.reset(token)
            self.store.release_run(run_id, owner)

    async def _produce(self, run_id: str, inputs: RunInput) -> WorkflowResult:
        brief, evidence = inputs.brief, inputs.evidence
        plan = await self.step(run_id, Role.RESEARCH, SourcePlan, (brief, inputs.sources, evidence))
        available = {s.source_id for s in inputs.sources.sources}
        if not set(plan.selected_source_ids) <= available:
            raise GateError("Research selected unregistered sources.")
        if plan.missing_evidence:
            self.store.state(run_id, "needs_evidence", self._run_owner.get())
            return WorkflowResult(
                run_id=run_id, state="needs_evidence", reason="; ".join(plan.missing_evidence)
            )
        sources = tuple(
            s for s in inputs.sources.sources if s.source_id in plan.selected_source_ids
        )
        evidence = Evidence(
            spans=tuple(s for s in evidence.spans if s.source_id in plan.selected_source_ids)
        )
        claims = await self.step(run_id, Role.EVIDENCE, Claims, (brief, evidence))
        validate_evidence(claims, evidence, sources)
        blueprint = await self.step(run_id, Role.DESIGN, Blueprint, (brief, claims))
        if not set(blueprint.claim_ids) <= {c.claim_id for c in claims.claims}:
            raise GateError("Blueprint references nonexistent claims.")
        feedback = Feedback(instructions="Create the initial material.")
        for revision in range(self.max_revisions + 1):
            material = await self.step(
                run_id, Role.AUTHOR, Material, (brief, blueprint, claims, evidence, feedback)
            )
            validate_material(material, claims)
            blind = BlindExam(
                exercises=tuple(
                    BlindExercise(
                        exercise_id=e.exercise_id,
                        prompt=e.prompt,
                        instruction=e.instruction,
                        options=e.options,
                    )
                    for e in material.exercises
                )
            )
            # The solver receives neither author answers nor explanations.
            solutions = await self.step(run_id, Role.TEACHING, Solutions, (brief, blind))
            if {s.exercise_id for s in solutions.solutions} != {
                e.exercise_id for e in material.exercises
            } or len(solutions.solutions) != len(material.exercises):
                raise GateError("Independent solver must answer every exercise exactly once.")
            results = await asyncio.gather(
                self.step(run_id, Role.KNOWLEDGE, Review, (brief, claims, evidence, material)),
                self.step(
                    run_id, Role.TEACHING, Review, (brief, blueprint, evidence, material, solutions)
                ),
                return_exceptions=True,
            )
            # Join both independent attempts before propagating a failure or resuming the run.
            for result in results:
                if isinstance(result, BaseException):
                    raise result
            knowledge, teaching = results
            assert isinstance(knowledge, Review) and isinstance(teaching, Review)
            span_ids = {s.span_id for s in evidence.spans}
            for review in (knowledge, teaching):
                if any(
                    s not in span_ids for issue in review.issues for s in issue.evidence_span_ids
                ):
                    raise GateError("Reviewer cited nonexistent evidence.")
            answers = {s.exercise_id: s.answer for s in solutions.solutions}
            mismatch = any(
                answers[e.exercise_id] not in (e.answer, *e.accepted_answers)
                for e in material.exercises
            )
            conservative_score = sum(
                min(a, b) * weight / 5
                for a, b, weight in zip(
                    knowledge.dimensions, teaching.dimensions, (30, 25, 20, 15, 10), strict=True
                )
            )
            if knowledge.passes and teaching.passes and conservative_score >= 85 and not mismatch:
                catalog = await self.step(run_id, Role.CATALOG, Catalog, (brief, material))
                packet = Packet(
                    brief=brief,
                    sources=sources,
                    evidence=evidence,
                    claims=claims,
                    blueprint=blueprint,
                    material=material,
                    knowledge_review=knowledge,
                    teaching_review=teaching,
                    catalog=catalog,
                )
                version = self.store.save_packet(run_id, packet, self._run_owner.get())
                return WorkflowResult(
                    run_id=run_id, state=self.store.version_state(version), version_id=version
                )
            if revision == self.max_revisions:
                break
            if (
                "dispute" in (knowledge.verdict, teaching.verdict)
                or knowledge.passes != teaching.passes
                or mismatch
            ):
                decision = await self.step(
                    run_id,
                    Role.ARBITER,
                    Decision,
                    (claims, evidence, material, knowledge, teaching, solutions),
                )
                if not set(decision.evidence_span_ids) <= span_ids:
                    raise GateError("Arbitration cited nonexistent evidence.")
                if decision.decision != "revise":
                    self.store.state(run_id, decision.decision, self._run_owner.get())
                    return WorkflowResult(
                        run_id=run_id, state=decision.decision, reason=decision.rationale
                    )
                feedback = Feedback(
                    instructions=f"Revision {revision + 1}: {decision.revision_instructions}"
                )
            else:
                feedback = Feedback(
                    instructions=f"Revision {revision + 1}: {knowledge.model_dump_json()}\n{teaching.model_dump_json()}"
                )
        self.store.state(run_id, "needs_human", self._run_owner.get())
        return WorkflowResult(
            run_id=run_id,
            state="needs_human",
            reason="Bounded revision limit reached; inspect durable review tasks.",
        )
