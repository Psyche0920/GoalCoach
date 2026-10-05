"""Source-boundary tests with pinned transport and authentic export formats."""

import hashlib
import io
from pathlib import Path

import httpx
import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from goalcoach.materials.ingestion import IngestionService, TextExtractor
from goalcoach.materials.models import GateError, Source
from goalcoach.materials.sources import (
    PublicHTTPSClient,
    SocialMetadataService,
    SubtitleParser,
)
from goalcoach.materials.store import Workbench


class FixedResolver:
    def __init__(self, *addresses: str) -> None:
        self.addresses = addresses
        self.calls = 0

    async def resolve(self, host: str) -> tuple[str, ...]:
        self.calls += 1
        return self.addresses


def test_html_cleaning_prefers_main_and_keeps_table_boundaries() -> None:
    parser = TextExtractor()
    parser.feed(
        "<header>Menu</header><main><h1>Greetings</h1><nav>Hidden menu</nav>"
        "<table><tr><td>你好</td><td>nǐ hǎo</td><td>Hello</td></tr></table>"
        "<script>secret()</script></main><footer>Legal footer</footer>"
    )
    text = "".join(parser.parts)
    assert "你好 | nǐ hǎo | Hello" in text
    assert "Greetings" in text
    assert "menu" not in text.lower() and "secret" not in text and "footer" not in text


def approved_source() -> Source:
    return Source(
        source_id="authorized-export",
        title="Creator-owned test export",
        category="professional_social",
        publisher="Test author",
        edition="1",
        url="https://example.org/lesson",
        rights_evidence="Test fixture owned by test author.",
        allowed_uses=("analysis",),
        approved_by="test-owner",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "::1",
        "fc00::1",
        "224.0.0.1",
        "ff02::1",
        "4000::1",
    ],
)
async def test_private_dns_is_rejected_before_transport(address: str) -> None:
    client = PublicHTTPSClient(FixedResolver("8.8.8.8", address))
    with pytest.raises(GateError, match="public addresses"):
        await client.fetch(
            "https://example.org/x", frozenset({"example.org"}), frozenset({"text/plain"})
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1/x",
        "https://[::1]/x",
        "https://user:secret@example.org/x",
        "https://example.org:444/x",
        "http://example.org/x",
        "https://example.org:bad/x",
        "https://localhost/x",
        "https://example.org/x#fragment",
    ],
)
async def test_invalid_targets_are_rejected_without_resolution(url: str) -> None:
    resolver = FixedResolver("8.8.8.8")
    client = PublicHTTPSClient(resolver)
    with pytest.raises(GateError):
        await client.fetch(
            url,
            frozenset({"example.org", "127.0.0.1", "::1", "localhost"}),
            frozenset({"text/plain"}),
        )
    assert resolver.calls == 0


@pytest.mark.asyncio
async def test_public_address_is_pinned_with_original_tls_hostname() -> None:
    resolver = FixedResolver("8.8.8.8")

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "8.8.8.8"
        assert request.headers["host"] == "example.org"
        assert request.extensions["sni_hostname"] == "example.org"
        return httpx.Response(
            200, headers={"content-type": "text/plain; charset=utf-8"}, text="你好"
        )

    client = PublicHTTPSClient(resolver, httpx.MockTransport(respond))
    result = await client.fetch(
        "https://example.org/lesson", frozenset({"example.org"}), frozenset({"text/plain"})
    )
    assert result.body.decode() == "你好"
    assert resolver.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,content_type", [(302, "text/plain"), (206, "text/plain"), (200, "application/pdf")]
)
async def test_redirect_partial_and_wrong_content_are_rejected(
    status: int, content_type: str
) -> None:
    client = PublicHTTPSClient(
        FixedResolver("8.8.8.8"),
        httpx.MockTransport(
            lambda _: httpx.Response(
                status,
                headers={"content-type": content_type, "location": "https://127.0.0.1/"},
                text="x",
            )
        ),
    )
    with pytest.raises(GateError):
        await client.fetch(
            "https://example.org/x", frozenset({"example.org"}), frozenset({"text/plain"})
        )


@pytest.mark.asyncio
async def test_large_remote_body_is_bounded() -> None:
    client = PublicHTTPSClient(
        FixedResolver("8.8.8.8"),
        httpx.MockTransport(
            lambda _: httpx.Response(
                200, headers={"content-type": "text/plain"}, content=b"x" * 1_000_001
            )
        ),
    )
    with pytest.raises(GateError, match="size limit"):
        await client.fetch(
            "https://example.org/x", frozenset({"example.org"}), frozenset({"text/plain"})
        )


@pytest.mark.asyncio
async def test_youtube_metadata_never_grants_content_rights() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/oembed"
        assert request.url.params["url"] == "https://www.youtube.com/watch?v=abcdefghijk"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "title": "Mandarin lesson",
                "author_name": "Creator",
                "author_url": "https://www.youtube.com/@creator",
                "provider_name": "YouTube",
                "html": "<untrusted embed>",
            },
        )

    service = SocialMetadataService(
        PublicHTTPSClient(FixedResolver("8.8.8.8"), httpx.MockTransport(respond))
    )
    metadata = await service.fetch("https://youtu.be/abcdefghijk")
    assert metadata.title == "Mandarin lesson"
    assert metadata.content_permission == "not_granted_by_metadata"
    assert "untrusted embed" not in metadata.model_dump_json()


@pytest.mark.asyncio
async def test_bilibili_captcha_does_not_become_teaching_evidence() -> None:
    service = SocialMetadataService(
        PublicHTTPSClient(
            FixedResolver("8.8.8.8"),
            httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    headers={"content-type": "text/html"},
                    text="<title>验证码_哔哩哔哩</title>",
                )
            ),
        )
    )
    with pytest.raises(GateError, match="creator export"):
        await service.fetch("https://www.bilibili.com/video/BV1234567890/")


@pytest.mark.parametrize(
    "suffix,text",
    [
        (".srt", "1\n00:00:01,500 --> 00:00:03,000\n你好\n"),
        (".vtt", "WEBVTT\n\ncue-1\n00:01.500 --> 00:03.000 align:start\n<c>你好</c>\n"),
        (".json", '{"body":[{"from":1.5,"to":3,"content":"你好","location":2}]}'),
    ],
)
def test_authorized_subtitle_formats(suffix: str, text: str) -> None:
    cues = SubtitleParser().parse(text, suffix)
    assert len(cues) == 1
    assert cues[0].start_seconds == 1.5 and cues[0].end_seconds == 3
    assert cues[0].text == "你好"


@pytest.mark.parametrize(
    "text",
    [
        "1\n00:00:03,000 --> 00:00:01,500\n你好",
        "1\n00:70:03,000 --> 00:71:01,500\n你好",
        "1\n00:00:01,500 --> 00:00:03,000\n   ",
        "not a subtitle file",
    ],
)
def test_invalid_subtitles_are_rejected(text: str) -> None:
    with pytest.raises(GateError):
        SubtitleParser().parse(text, ".srt")


def test_subtitle_import_preserves_original_hash_and_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "lesson.srt"
    raw = b"1\r\n00:00:01,500 --> 00:00:03,000\r\nHello owner@example.org\r\n"
    path.write_bytes(raw)
    store = Workbench(tmp_path / "workbench.db")
    spans = IngestionService(store).import_subtitles(approved_source(), path)
    assert spans[0].source_hash == hashlib.sha256(raw).hexdigest()
    assert "time=1.500-3.000" in spans[0].locator
    assert spans[0].text == "Hello [REDACTED EMAIL]"


def test_subtitle_import_enforces_analysis_permission(tmp_path: Path) -> None:
    source = approved_source().model_copy(update={"allowed_uses": ()})
    service = IngestionService(Workbench(tmp_path / "workbench.db"))
    with pytest.raises(GateError, match="permit analysis"):
        service.import_subtitles(source, tmp_path / "missing.srt")


def pdf_bytes(texts: tuple[str | None, ...], *, encrypted: bool = False) -> bytes:
    with PdfWriter() as writer, io.BytesIO() as buffer:
        for text in texts:
            page = writer.add_blank_page(width=612, height=792)
            if text is not None:
                font = DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/Font"),
                        NameObject("/Subtype"): NameObject("/Type1"),
                        NameObject("/BaseFont"): NameObject("/Helvetica"),
                    }
                )
                page[NameObject("/Resources")] = DictionaryObject(
                    {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
                )
                content = DecodedStreamObject()
                content.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii"))
                page[NameObject("/Contents")] = content
        if encrypted:
            writer.encrypt("test-password")
        writer.write(buffer)
        return buffer.getvalue()


def test_pdf_import_preserves_binary_hash_and_selected_page_locator(tmp_path: Path) -> None:
    path = tmp_path / "lesson.pdf"
    raw = pdf_bytes(("Other page", "Hello owner@example.org"))
    path.write_bytes(raw)
    service = IngestionService(Workbench(tmp_path / "workbench.db"))
    spans = service.import_pdf(approved_source(), path, (2,))
    assert len(spans) == 1
    assert spans[0].text == "Hello [REDACTED EMAIL]"
    assert spans[0].source_hash == hashlib.sha256(raw).hexdigest()
    assert spans[0].locator == "lesson.pdf:page=2:line=1:offset=0"


@pytest.mark.parametrize("pages", [(), (0,), (-1,), (1, 1), tuple(range(1, 22))])
def test_pdf_import_rejects_invalid_page_selection_before_reading(
    tmp_path: Path, pages: tuple[int, ...]
) -> None:
    service = IngestionService(Workbench(tmp_path / "workbench.db"))
    with pytest.raises(GateError, match="distinct PDF pages"):
        service.import_pdf(approved_source(), tmp_path / "missing.pdf", pages)


@pytest.mark.parametrize(
    "raw,pages,error",
    [
        (pdf_bytes(("Hello",)), (2,), "page range"),
        (pdf_bytes(("Hello",), encrypted=True), (1,), "Encrypted"),
        (b"not a pdf", (1,), "could not be extracted"),
        (pdf_bytes(("Hello", None)), (1, 2), "page 2 contains no usable native text"),
    ],
    ids=("out-of-range", "encrypted", "invalid-format", "image-only-page"),
)
def test_pdf_rejection_does_not_register_partial_evidence(
    tmp_path: Path, raw: bytes, pages: tuple[int, ...], error: str
) -> None:
    path = tmp_path / "invalid.pdf"
    path.write_bytes(raw)
    store = Workbench(tmp_path / "workbench.db")
    with pytest.raises(GateError, match=error):
        IngestionService(store).import_pdf(approved_source(), path, pages)
    assert store.sources() == ()
    assert store.spans() == ()


def test_pdf_input_limit_is_enforced(tmp_path: Path) -> None:
    path = tmp_path / "too-large.pdf"
    with path.open("wb") as file:
        file.truncate(IngestionService.MAX_PDF_BYTES + 1)
    service = IngestionService(Workbench(tmp_path / "workbench.db"))
    with pytest.raises(GateError, match="20 MB"):
        service.import_pdf(approved_source(), path, (1,))


def test_pdf_cumulative_text_limit_is_enforced(tmp_path: Path) -> None:
    path = tmp_path / "lesson.pdf"
    path.write_bytes(pdf_bytes(("Hello", "Again")))
    service = IngestionService(Workbench(tmp_path / "workbench.db"))
    service.MAX_BYTES = 9
    with pytest.raises(GateError, match="extraction limit"):
        service.import_pdf(approved_source(), path, (1, 2))
