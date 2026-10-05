"""Bounded text ingestion and explicit, allowlisted web collection."""

from __future__ import annotations

import hashlib
import io
import re
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from goalcoach.materials.models import GateError, Source, Span
from goalcoach.materials.sources import PublicHTTPSClient, SubtitleParser
from goalcoach.materials.store import Workbench


class TextExtractor(HTMLParser):
    _HIDDEN = frozenset({"script", "style", "nav", "footer", "noscript", "aside", "header"})
    _BLOCKS = frozenset({"p", "br", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0
        self.finished_main = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.finished_main:
            return
        if tag == "main":
            # Discard navigation preceding the page's semantic content region.
            self.parts.clear()
        if tag in self._HIDDEN:
            self.hidden += 1
        if tag in self._BLOCKS:
            self.parts.append("\n")
        if tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "main":
            self.finished_main = True
        if tag in self._HIDDEN:
            self.hidden = max(0, self.hidden - 1)
        if tag in self._BLOCKS and not self.finished_main:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden and not self.finished_main:
            self.parts.append(data)


class IngestionService:
    MAX_BYTES = 1_000_000
    MAX_PDF_BYTES = 20_000_000
    MAX_PDF_PAGES = 20

    def __init__(self, store: Workbench, client: PublicHTTPSClient | None = None) -> None:
        self.store = store
        self._client = client or PublicHTTPSClient()

    @staticmethod
    def _clean(text: str) -> str:
        clean = re.sub(r"[\t \u00a0]+", " ", text).strip()
        return re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED EMAIL]", clean)

    def import_text(self, source: Source, text: str, locator: str) -> tuple[Span, ...]:
        source.require("analysis")
        if len(text.encode()) > self.MAX_BYTES:
            raise GateError("Split large documents into files smaller than 1 MB.")
        raw_hash = hashlib.sha256(text.encode()).hexdigest()
        spans: list[Span] = []
        seen: set[str] = set()
        for line_number, line in enumerate(text.splitlines(), 1):
            clean = self._clean(line)
            if not clean or clean in seen:
                continue
            seen.add(clean)
            for offset in range(0, len(clean), 2000):
                fragment = clean[offset : offset + 2000]
                key = hashlib.sha256(
                    f"{source.source_id}:{raw_hash}:{line_number}:{offset}".encode()
                ).hexdigest()
                spans.append(
                    Span(
                        span_id=key,
                        source_id=source.source_id,
                        locator=f"{locator}:line={line_number}:offset={offset}",
                        text=fragment,
                        source_hash=raw_hash,
                    )
                )
        if not spans:
            raise GateError("No usable text found.")
        self.store.register(source)
        self.store.save_spans(tuple(spans))
        return tuple(spans)

    def import_file(self, source: Source, path: Path) -> tuple[Span, ...]:
        try:
            if path.stat().st_size > self.MAX_BYTES:
                raise GateError("Input exceeds the 1 MB ingestion limit.")
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise GateError("Cannot read UTF-8 source file.") from exc
        return self.import_text(source, text, path.name)

    def import_subtitles(self, source: Source, path: Path) -> tuple[Span, ...]:
        source.require("analysis")
        try:
            if path.stat().st_size > self.MAX_BYTES:
                raise GateError("Subtitle export exceeds the 1 MB limit.")
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise GateError("Cannot read UTF-8 subtitle export.") from exc
        cues = SubtitleParser().parse(text, path.suffix)
        raw_hash = hashlib.sha256(raw).hexdigest()
        spans: list[Span] = []
        for index, cue in enumerate(cues, 1):
            clean = self._clean(cue.text)
            for offset in range(0, len(clean), 2000):
                key = hashlib.sha256(
                    f"{source.source_id}:{raw_hash}:{index}:{offset}".encode()
                ).hexdigest()
                spans.append(
                    Span(
                        span_id=key,
                        source_id=source.source_id,
                        locator=(
                            f"{path.name}:cue={index}:time={cue.start_seconds:.3f}"
                            f"-{cue.end_seconds:.3f}:offset={offset}"
                        ),
                        text=clean[offset : offset + 2000],
                        source_hash=raw_hash,
                    )
                )
        if not spans:
            raise GateError("No usable subtitle text found.")
        self.store.register(source)
        self.store.save_spans(tuple(spans))
        return tuple(spans)

    def import_pdf(self, source: Source, path: Path, pages: tuple[int, ...]) -> tuple[Span, ...]:
        """Import explicit native-text pages, preserving the original document hash."""
        source.require("analysis")
        if (
            not pages
            or len(pages) > self.MAX_PDF_PAGES
            or len(set(pages)) != len(pages)
            or any(page < 1 for page in pages)
        ):
            raise GateError("Select between 1 and 20 distinct PDF pages using 1-based numbers.")
        try:
            if path.stat().st_size > self.MAX_PDF_BYTES:
                raise GateError("PDF input exceeds the 20 MB limit.")
            with path.open("rb") as file:
                raw = file.read(self.MAX_PDF_BYTES + 1)
            if len(raw) > self.MAX_PDF_BYTES:
                raise GateError("PDF input exceeds the 20 MB limit.")
        except OSError as exc:
            raise GateError("Cannot read PDF source file.") from exc

        raw_hash = hashlib.sha256(raw).hexdigest()
        spans: list[Span] = []
        extracted_bytes = 0
        try:
            with io.BytesIO(raw) as stream:
                reader = PdfReader(stream, strict=True)
                if reader.is_encrypted:
                    raise GateError("Encrypted PDF sources are not supported.")
                if max(pages) > len(reader.pages):
                    raise GateError("A selected PDF page is outside the document's page range.")
                for page_number in pages:
                    text = reader.pages[page_number - 1].extract_text()
                    extracted_bytes += len(text.encode("utf-8"))
                    if extracted_bytes > self.MAX_BYTES:
                        raise GateError("Selected PDF text exceeds the 1 MB extraction limit.")
                    page_spans: list[Span] = []
                    seen: set[str] = set()
                    for line_number, line in enumerate(text.splitlines(), 1):
                        clean = self._clean(line)
                        if not clean or clean in seen:
                            continue
                        seen.add(clean)
                        for offset in range(0, len(clean), 2000):
                            key = hashlib.sha256(
                                f"{source.source_id}:{raw_hash}:page={page_number}:"
                                f"line={line_number}:offset={offset}".encode()
                            ).hexdigest()
                            page_spans.append(
                                Span(
                                    span_id=key,
                                    source_id=source.source_id,
                                    locator=(
                                        f"{path.name}:page={page_number}:line={line_number}"
                                        f":offset={offset}"
                                    ),
                                    text=clean[offset : offset + 2000],
                                    source_hash=raw_hash,
                                )
                            )
                    if not page_spans:
                        raise GateError(
                            f"PDF page {page_number} contains no usable native text; "
                            "provide an authorized, reviewed text export. OCR is not supported."
                        )
                    spans.extend(page_spans)
        except (PdfReadError, ValueError, KeyError, RecursionError, UnicodeError) as exc:
            raise GateError(
                "PDF text could not be extracted safely from the selected pages."
            ) from exc
        # Validate the entire selection before adding any source or evidence to the workbench.
        self.store.register(source)
        self.store.save_spans(tuple(spans))
        return tuple(spans)

    async def collect(self, source: Source, allowed_hosts: frozenset[str]) -> tuple[Span, ...]:
        source.require("analysis")
        document = await self._client.fetch(
            source.url, allowed_hosts, frozenset({"text/plain", "text/html"})
        )
        try:
            text = document.body.decode("utf-8")
            if "text/html" in document.content_type:
                parser = TextExtractor()
                parser.feed(text)
                text = "".join(parser.parts)
        except UnicodeError as exc:
            raise GateError("Source collection failed; use an authorized manual export.") from exc
        return self.import_text(source, text, source.url)
