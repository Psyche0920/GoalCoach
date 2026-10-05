"""Loopback-only, human-gated material review without external browser assets."""

from __future__ import annotations

import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Annotated
from urllib.parse import parse_qs, quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import Field, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from goalcoach.materials.models import GateError, Packet, Record, Review, StorageError, UsageSummary
from goalcoach.materials.publication import PublicationService
from goalcoach.materials.store import Workbench

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
_LOCAL_HOST = re.compile(r"(?:localhost|127\.0\.0\.1|\[::1\])(?::([0-9]{1,5}))?\Z")
_MAX_FORM_BYTES = 32_768


class ApprovalForm(Record):
    version_id: Digest
    expected_hash: Digest
    reviewer: str = Field(min_length=1, max_length=160)


class PublishForm(Record):
    version_ids: tuple[Digest, ...] = Field(min_length=1, max_length=100)


@dataclass(frozen=True, slots=True)
class FormFields:
    values: Mapping[str, tuple[str, ...]]

    def single(self, name: str) -> str:
        values = self.values.get(name, ())
        if len(values) != 1:
            raise HTTPException(422, f"Provide exactly one {name} field.")
        return values[0]

    def require_fields(self, allowed: frozenset[str]) -> None:
        if self.values.keys() - allowed:
            raise HTTPException(422, "Unexpected form fields.")


class LocalReviewSecurityMiddleware(BaseHTTPMiddleware):
    """Prevent remote hosts and cross-origin writes to a local review process."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        host_values = request.headers.getlist("host")
        host = host_values[0] if len(host_values) == 1 else ""
        match = _LOCAL_HOST.fullmatch(host)
        valid_host = match is not None and (
            match.group(1) is None or 1 <= int(match.group(1)) <= 65535
        )
        if not valid_host:
            response: Response = HTMLResponse("Local host required.", status_code=403)
        elif request.method not in {"GET", "HEAD", "OPTIONS"} and (
            request.headers.get("origin") != f"{request.url.scheme}://{host}"
            or request.headers.get("sec-fetch-site") == "cross-site"
        ):
            response = HTMLResponse("Same-origin form submission required.", status_code=403)
        else:
            response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "Content-Security-Policy": (
                    "default-src 'none'; style-src 'unsafe-inline'; "
                    "form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
                ),
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
            }
        )
        return response


class ReviewDashboard:
    """Render immutable evidence and delegate explicit writes to existing gates."""

    def __init__(self, store: Workbench, release_root: Path) -> None:
        self.store = store
        self.release_root = release_root.resolve()
        self.publication = PublicationService(store)
        self.csrf_token = secrets.token_urlsafe(32)

    def index(self) -> HTMLResponse:
        run_summaries = self.store.runs()
        version_summaries = self.store.versions()
        packets = {
            version.version_id: self.store.packet(version.version_id)
            for version in version_summaries
        }
        run_titles: dict[str, list[str]] = {}
        with self.store.connection() as db:
            for row in db.execute("SELECT run_id,version_id FROM run_versions ORDER BY rowid DESC"):
                packet = packets.get(str(row[1]))
                if packet is not None:
                    titles = run_titles.setdefault(str(row[0]), [])
                    if packet.material.title_en not in titles:
                        titles.append(packet.material.title_en)
        runs = "".join(
            f'<tr><td><a href="/runs/{quote(run.run_id, safe="")}">'
            + escape("; ".join(run_titles.get(run.run_id, [])) or run.run_id)
            + "</a>"
            f"</td><td>{escape(run.state)}</td><td>{run.request_count}</td></tr>"
            for run in run_summaries
        )
        versions = "".join(
            "<tr><td>"
            + (
                f'<input type="checkbox" name="version_ids" value="{escape(version.version_id)}" '
                f'aria-label="Select version {escape(version.version_id)}">'
                if version.state in {"approved", "published"}
                else "Review first"
            )
            + f'</td><td><a href="/versions/{quote(version.version_id, safe="")}">'
            + escape(packets[version.version_id].material.title_en)
            + "</a><br><small>"
            + escape(packets[version.version_id].brief.concept_id)
            + f"</small></td><td>{escape(version.state)}</td></tr>"
            for version in version_summaries
        )
        editorial_notice = (
            '<section aria-labelledby="editorial-usage"><h2 id="editorial-usage">'
            "Codex editorial work</h2><p><strong>The application-provider counters below "
            "exclude Codex editorial work.</strong> This library includes an actual "
            "Codex editorial batch whose token usage and cost are unknown. "
            "The provider figures are not a total cost for producing these materials.</p></section>"
            if any(run.run_id.startswith("editorial-") for run in run_summaries)
            else ""
        )
        return self.page(
            "Teaching materials review",
            "<p>Review each exact material version, approve it as an identified teacher, "
            "then select approved versions for a release. Include their prerequisites.</p>"
            + editorial_notice
            + self.usage_html(self.store.usage())
            + "<h2>Production runs</h2><table><thead><tr><th>Run</th><th>State</th>"
            "<th>Model requests</th></tr></thead><tbody>"
            + (runs or '<tr><td colspan="3">No production runs yet.</td></tr>')
            + "</tbody></table><h2>Material versions</h2>"
            '<form method="post" action="/publish">'
            + self.csrf_field()
            + "<table><thead><tr><th>Select</th><th>Material</th><th>State</th>"
            "</tr></thead><tbody>"
            + (versions or '<tr><td colspan="3">No material versions yet.</td></tr>')
            + '</tbody></table><button type="submit">Publish selected approved versions</button>'
            "</form>",
        )

    def version(self, version_id: str) -> HTMLResponse:
        summary = next(
            (version for version in self.store.versions() if version.version_id == version_id),
            None,
        )
        if summary is None:
            raise HTTPException(404, "Unknown material version.")
        packet = self.store.packet(version_id)
        state = self.store.version_state(version_id)
        approval = ""
        if state == "awaiting_approval":
            approval = (
                '<h2>Human approval</h2><form method="post" action="/approve">'
                + self.csrf_field()
                + f'<input type="hidden" name="version_id" value="{escape(version_id)}">'
                + f'<input type="hidden" name="expected_hash" value="{packet.digest()}">'
                "<p>Approving confirms that you reviewed this complete version, its evidence, "
                "source rights, and independent reviews.</p>"
                '<label>Your name <input name="reviewer" required maxlength="160" '
                'autocomplete="name"></label> '
                '<button type="submit">Approve this exact version</button></form>'
            )
        content = (
            f"<p>State: <strong>{escape(state)}</strong></p>"
            f"<p>Version and review hash: <code>{escape(version_id)}</code></p>"
            f"<p>Concept: {escape(packet.brief.concept_id)}. Prerequisites: "
            f"{escape(', '.join(packet.brief.prerequisite_ids) or 'None')}.</p>"
            f"<p>Knowledge review: {packet.knowledge_review.score:.0f}/100; "
            f"teaching review: {packet.teaching_review.score:.0f}/100; "
            f"combined quality gate: {'passed' if packet.quality_passes else 'blocked'}.</p>"
            + self.material_html(packet)
            + "<h2>Independent reviews</h2>"
            + self.review_html("Knowledge review", packet.knowledge_review)
            + self.review_html("Teaching review", packet.teaching_review)
            + "<details><summary>Complete immutable packet</summary>"
            + self.json_html(packet.model_dump_json(indent=2))
            + "</details><h2>Agent review and dispute history</h2>"
            + self.tasks_html(summary.run_id)
            + approval
        )
        return self.page(packet.material.title_en, content)

    def run(self, run_id: str) -> HTMLResponse:
        summary = next((run for run in self.store.runs() if run.run_id == run_id), None)
        if summary is None:
            raise HTTPException(404, "Unknown production run.")
        return self.page(
            f"Production run {run_id}",
            f"<p>State: {escape(summary.state)}. Model requests: {summary.request_count}.</p>"
            + self.usage_html(self.store.usage(run_id))
            + "<h2>Agent review and dispute history</h2>"
            + self.tasks_html(run_id),
        )

    def approve(self, form: ApprovalForm) -> HTMLResponse:
        self.store.approve(form.version_id, form.expected_hash, form.reviewer)
        return self.page(
            "Version approved",
            f"<p>{escape(form.reviewer)} approved the exact reviewed hash.</p>"
            f'<p><a href="/versions/{form.version_id}">View approved version</a></p>'
            '<p>Select it on the <a href="/">review home</a> to publish.</p>',
        )

    def publish(self, form: PublishForm) -> HTMLResponse:
        folder = self.publication.export_many(form.version_ids, self.release_root)
        return self.page(
            "Release published",
            f"<p>Published {len(form.version_ids)} approved material version(s).</p>"
            f"<p>Release folder: <code>{escape(str(folder))}</code></p>"
            "<p>The folder contains the teaching database, materials, review report, "
            "and integrity manifest.</p>",
        )

    async def form(self, request: Request) -> FormFields:
        if request.headers.get("content-type", "").split(";", 1)[0].strip() != (
            "application/x-www-form-urlencoded"
        ):
            raise HTTPException(415, "Use a URL-encoded review form.")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > _MAX_FORM_BYTES:
                raise HTTPException(413, "Review form is too large.")
        try:
            parsed = parse_qs(
                body.decode("utf-8"),
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=104,
            )
        except (UnicodeDecodeError, ValueError) as exc:
            raise HTTPException(422, "Invalid review form encoding.") from exc
        fields = FormFields({name: tuple(values) for name, values in parsed.items()})
        tokens = fields.values.get("csrf_token", ())
        if len(tokens) != 1 or not secrets.compare_digest(
            tokens[0].encode("utf-8"), self.csrf_token.encode("ascii")
        ):
            raise HTTPException(403, "Invalid review session token. Reload the review page.")
        return fields

    def csrf_field(self) -> str:
        return f'<input type="hidden" name="csrf_token" value="{self.csrf_token}">'

    def tasks_html(self, run_id: str) -> str:
        tasks = self.store.tasks(run_id)
        return (
            "".join(
                "<details><summary>"
                f"{escape(task.role)} — {escape(task.state)} — {escape(task.task_id)}"
                "</summary>"
                + self.json_html(task.result_json or "No completed result recorded.")
                + "</details>"
                for task in tasks
            )
            or "<p>No agent task history recorded.</p>"
        )

    @staticmethod
    def material_html(packet: Packet) -> str:
        material = packet.material
        cards = "".join(
            f"<article><h3>{escape(card.card_type.replace('_', ' ').title())}</h3>"
            f"<p><strong>{escape(card.text_zh)}</strong> · {escape(card.pinyin)}</p>"
            f"<p>{escape(card.meaning_en)}</p><p>{escape(card.explanation_en)}</p>"
            f'<p class="note">Evidence claims: {escape(", ".join(card.claim_ids))}</p></article>'
            for card in material.cards
        )
        exercises = "".join(
            f"<article><h3>Exercise {number}</h3><p>{escape(exercise.prompt)}</p>"
            f"<p>{escape(exercise.instruction)}</p><ol>"
            + "".join(f"<li>{escape(option)}</li>" for option in exercise.options)
            + f"</ol><p><strong>Answer:</strong> {escape(exercise.answer)}</p>"
            f"<p>{escape(exercise.explanation)}</p>"
            f'<p class="note">Evidence claims: {escape(", ".join(exercise.claim_ids))}</p></article>'
            for number, exercise in enumerate(material.exercises, 1)
        )
        sources = "".join(
            f"<article><h3>{escape(source.title)}</h3>"
            f"<p>{escape(source.publisher)} · {escape(source.edition)}</p>"
            f"<p>Source reference: {escape(source.url or source.source_id)}</p>"
            f"<p>Rights evidence: {escape(source.rights_evidence)}</p>"
            f"<p>Permitted uses: {escape(', '.join(source.allowed_uses))}</p></article>"
            for source in packet.sources
        )
        return (
            f"<h2>Teaching material · {escape(material.title_zh)}</h2>"
            f"<p>Objective: {escape(packet.brief.objective)}</p>"
            f"<p>Estimated time: {material.estimated_minutes} minutes.</p>"
            + cards
            + "<h2>Exercises and answer key</h2>"
            + exercises
            + f"<h2>Teacher notes</h2><p>{escape(material.teacher_notes)}</p>"
            + "<h2>Sources and usage rights</h2>"
            + sources
        )

    @staticmethod
    def review_html(label: str, review: Review) -> str:
        issues = "".join(
            f"<li><strong>{escape(issue.severity)}: {escape(issue.location)}</strong> — "
            f"{escape(issue.finding)}</li>"
            for issue in review.issues
        )
        return (
            f"<article><h3>{escape(label)} · {escape(review.verdict)} · {review.score:.0f}/100</h3>"
            f"<p>{escape(review.rationale)}</p>"
            f"<p>Accuracy {review.accuracy}/5 · Teachability {review.teachability}/5 · "
            f"Evidence {review.evidence}/5 · Difficulty {review.difficulty}/5 · "
            f"Naturalness {review.naturalness}/5</p>"
            + (f"<ul>{issues}</ul>" if issues else "<p>No review issues recorded.</p>")
            + "</article>"
        )

    @staticmethod
    def usage_html(usage: UsageSummary) -> str:
        return (
            "<h2>Model usage</h2>"
            f"<p>{usage.attempts} attempts; {usage.measured_attempts} measured; "
            f"{usage.input_tokens} input tokens; {usage.output_tokens} output tokens.</p>"
            f"<p>Known estimated cost: USD {usage.known_estimated_cost_usd:.6f} "
            f"({usage.priced_attempts}/{usage.attempts} attempts priced). "
            "Unpriced attempts are not counted as free.</p>"
        )

    @staticmethod
    def json_html(value: str) -> str:
        return f"<pre>{escape(value)}</pre>"

    @staticmethod
    def page(title: str, body: str, status_code: int = 200) -> HTMLResponse:
        return HTMLResponse(
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{escape(title)}</title>"
            "<style>body{font:16px/1.5 system-ui,sans-serif;max-width:1100px;margin:32px auto;"
            "padding:0 20px;color:#17252c;background:#f6f8f9}a{color:#075f82}"
            "h1,h2{line-height:1.25}table{width:100%;border-collapse:collapse;background:white}"
            "td,th{text-align:left;padding:10px;border-bottom:1px solid #d7dfe3;overflow-wrap:anywhere}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:18px;"
            "border:1px solid #d7dfe3;border-radius:6px}code{overflow-wrap:anywhere}"
            "details{margin:12px 0}summary{cursor:pointer}button{background:#075f82;color:white;"
            "padding:10px 16px;border:0;border-radius:5px;margin:12px 0;cursor:pointer}"
            "input{padding:8px}form{padding:16px;background:#eef4f6;border-radius:6px}"
            "article{padding:12px 20px;margin:12px 0;background:white;border:1px solid #d7dfe3;"
            "border-radius:6px}.note{font-size:14px;color:#526770}"
            '</style></head><body><nav><a href="/">Review home</a></nav>'
            f"<main><h1>{escape(title)}</h1>{body}</main></body></html>",
            status_code=status_code,
        )


def create_review_app(store: Workbench, release_root: Path) -> FastAPI:
    """Create a local dashboard; the caller must bind its server to a loopback address."""
    dashboard = ReviewDashboard(store, release_root)
    app = FastAPI(title="Materials review", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(LocalReviewSecurityMiddleware)

    @app.exception_handler(GateError)
    async def gate_error(_request: Request, exc: GateError) -> HTMLResponse:
        return dashboard.page("Review action blocked", f"<p>{escape(str(exc))}</p>", 409)

    @app.exception_handler(StorageError)
    async def storage_error(_request: Request, _exc: StorageError) -> HTMLResponse:
        return dashboard.page("Storage unavailable", "<p>Cannot complete this operation.</p>", 503)

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return dashboard.index()

    @app.get("/versions/{version_id}", response_class=HTMLResponse)
    def version(version_id: str) -> HTMLResponse:
        return dashboard.version(version_id)

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def run(run_id: str) -> HTMLResponse:
        return dashboard.run(run_id)

    @app.post("/approve", response_class=HTMLResponse)
    async def approve(request: Request) -> HTMLResponse:
        fields = await dashboard.form(request)
        fields.require_fields(frozenset({"csrf_token", "version_id", "expected_hash", "reviewer"}))
        try:
            form = ApprovalForm(
                version_id=fields.single("version_id"),
                expected_hash=fields.single("expected_hash"),
                reviewer=fields.single("reviewer"),
            )
        except ValidationError as exc:
            raise HTTPException(
                422, "Provide a version hash and an identified human reviewer."
            ) from exc
        return await run_in_threadpool(dashboard.approve, form)

    @app.post("/publish", response_class=HTMLResponse)
    async def publish(request: Request) -> HTMLResponse:
        fields = await dashboard.form(request)
        fields.require_fields(frozenset({"csrf_token", "version_ids"}))
        try:
            form = PublishForm(version_ids=fields.values.get("version_ids", ()))
        except ValidationError as exc:
            raise HTTPException(422, "Select at least one approved material version.") from exc
        return await run_in_threadpool(dashboard.publish, form)

    return app
