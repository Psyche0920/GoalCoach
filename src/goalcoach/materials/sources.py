"""Bounded public-source access and typed, permission-neutral social metadata."""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Literal, Protocol, Self
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from goalcoach.materials.models import GateError, Record, Text


class AddressResolver(Protocol):
    async def resolve(self, host: str) -> tuple[str, ...]: ...


class SystemAddressResolver:
    async def resolve(self, host: str) -> tuple[str, ...]:
        try:
            records = await asyncio.get_running_loop().getaddrinfo(
                host, 443, type=socket.SOCK_STREAM
            )
        except OSError as exc:
            raise GateError("Source hostname could not be resolved.") from exc
        return tuple(dict.fromkeys(str(record[4][0]) for record in records))


@dataclass(frozen=True, slots=True)
class RemoteDocument:
    url: str
    content_type: str
    body: bytes


class PublicHTTPSClient:
    """Pin one validated public address while retaining TLS hostname verification."""

    MAX_BYTES = 1_000_000

    def __init__(
        self,
        resolver: AddressResolver | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._resolver = resolver or SystemAddressResolver()
        self._transport = transport

    @staticmethod
    def _is_public_address(address: str) -> bool:
        parsed = ipaddress.ip_address(address)
        return parsed.is_global and not parsed.is_multicast and not parsed.is_reserved

    async def fetch(
        self, url: str, allowed_hosts: frozenset[str], content_types: frozenset[str]
    ) -> RemoteDocument:
        try:
            parsed = urlsplit(url)
            host = parsed.hostname or ""
            valid = (
                parsed.scheme == "https"
                and host in allowed_hosts
                and not parsed.username
                and not parsed.password
                and parsed.port in {None, 443}
                and not parsed.fragment
            )
        except ValueError as exc:
            raise GateError("Source URL is invalid.") from exc
        if (
            not valid
            or host in {"localhost", "localhost.localdomain"}
            or host.endswith((".local", ".internal", ".localhost"))
        ):
            raise GateError("Collection requires an explicitly allowed public HTTPS host.")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise GateError("Literal-address collection targets are not supported.")

        try:
            async with asyncio.timeout(25):
                addresses = await self._resolver.resolve(host)
                if not addresses or not all(
                    self._is_public_address(address) for address in addresses
                ):
                    raise GateError("Source DNS must resolve exclusively to public addresses.")
                # Connect to the checked address: a second DNS lookup would permit rebinding.
                target = httpx.URL(url).copy_with(host=addresses[0])
                async with (
                    httpx.AsyncClient(
                        timeout=20,
                        follow_redirects=False,
                        trust_env=False,
                        transport=self._transport,
                    ) as client,
                    client.stream(
                        "GET",
                        target,
                        headers={"Host": host, "User-Agent": "TeachingMaterials/0.2"},
                        extensions={"sni_hostname": host},
                    ) as response,
                ):
                    response.raise_for_status()
                    if response.status_code != 200:
                        raise GateError("Collection did not return a complete document.")
                    content_type = response.headers.get("content-type", "").split(";", 1)[0]
                    if content_type.strip().lower() not in content_types:
                        raise GateError("Use an authorized export for this content type.")
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > self.MAX_BYTES:
                            raise GateError("Remote document exceeds the 1 MB size limit.")
                    return RemoteDocument(url, content_type, bytes(data))
        except (httpx.HTTPError, TimeoutError, ValueError) as exc:
            raise GateError("Source collection failed; use an authorized manual export.") from exc


class SocialMetadata(Record):
    platform: Literal["youtube", "bilibili"]
    url: Text
    title: Text
    publisher: Text
    publisher_url: str = ""
    content_permission: Literal["not_granted_by_metadata"] = "not_granted_by_metadata"


class _YouTubeOEmbed(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: Text
    author_name: Text
    author_url: str
    provider_name: Literal["YouTube"]


class _OpenGraphParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.author = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        attributes = dict(attrs)
        name = attributes.get("property") or attributes.get("name")
        if name == "og:title":
            self.title = attributes.get("content") or ""
        if name in {"author", "og:video:actor"}:
            self.author = attributes.get("content") or ""


class SocialMetadataService:
    def __init__(self, client: PublicHTTPSClient | None = None) -> None:
        self._client = client or PublicHTTPSClient()

    async def fetch(self, url: str) -> SocialMetadata:
        """Discover public metadata; this never grants textbook or transcript rights."""
        try:
            parsed = urlsplit(url)
            if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
                raise GateError("Social source must be an ordinary HTTPS platform URL.")
        except ValueError as exc:
            raise GateError("Social source URL is invalid.") from exc
        host = parsed.hostname
        if host in {"www.youtube.com", "youtube.com", "youtu.be"}:
            video_id = (
                parsed.path.removeprefix("/")
                if host == "youtu.be"
                else parse_qs(parsed.query).get("v", [""])[0]
            )
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                raise GateError("Use a YouTube watch URL containing one video ID.")
            canonical = f"https://www.youtube.com/watch?v={video_id}"
            endpoint = "https://www.youtube.com/oembed?" + urlencode(
                {"url": canonical, "format": "json"}
            )
            document = await self._client.fetch(
                endpoint, frozenset({"www.youtube.com"}), frozenset({"application/json"})
            )
            try:
                metadata = _YouTubeOEmbed.model_validate_json(document.body)
                return SocialMetadata(
                    platform="youtube",
                    url=canonical,
                    title=metadata.title,
                    publisher=metadata.author_name,
                    publisher_url=metadata.author_url,
                )
            except ValidationError as exc:
                raise GateError("YouTube returned invalid public metadata.") from exc
        if host in {"www.bilibili.com", "bilibili.com"}:
            if not re.fullmatch(r"/video/BV[A-Za-z0-9]{10}/?", parsed.path):
                raise GateError("Use a Bilibili video URL containing one BV identifier.")
            canonical = "https://www.bilibili.com" + parsed.path.rstrip("/") + "/"
            document = await self._client.fetch(
                canonical, frozenset({"www.bilibili.com"}), frozenset({"text/html"})
            )
            parser = _OpenGraphParser()
            try:
                parser.feed(document.body.decode("utf-8"))
                if not parser.title or not parser.author:
                    raise GateError(
                        "Bilibili did not expose complete static metadata; use a creator export."
                    )
                return SocialMetadata(
                    platform="bilibili",
                    url=canonical,
                    title=parser.title,
                    publisher=parser.author,
                )
            except (UnicodeError, ValidationError) as exc:
                raise GateError("Bilibili returned invalid public metadata.") from exc
        raise GateError("Supported social metadata platforms are YouTube and Bilibili.")


class SubtitleCue(Record):
    start_seconds: float = Field(ge=0, allow_inf_nan=False)
    end_seconds: float = Field(gt=0, allow_inf_nan=False)
    text: Text

    @model_validator(mode="after")
    def check_timing(self) -> Self:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Subtitle cue must end after it starts.")
        return self


class _BilibiliCue(BaseModel):
    model_config = ConfigDict(extra="ignore")
    start: float = Field(alias="from", ge=0, allow_inf_nan=False)
    end: float = Field(alias="to", gt=0, allow_inf_nan=False)
    content: Text


class _BilibiliSubtitles(BaseModel):
    model_config = ConfigDict(extra="ignore")
    body: tuple[_BilibiliCue, ...] = Field(min_length=1, max_length=5000)


class SubtitleParser:
    """Parse creator-authorized exports without downloading a platform's media."""

    _TIMING = re.compile(
        r"^(\d{1,3}:)?(\d{2}):(\d{2})[,.](\d{3})\s+-->\s+"
        r"(\d{1,3}:)?(\d{2}):(\d{2})[,.](\d{3})(?:\s+.*)?$"
    )

    @staticmethod
    def _seconds(hours: str | None, minutes: str, seconds: str, millis: str) -> float:
        if int(minutes) >= 60 or int(seconds) >= 60:
            raise GateError("Subtitle timestamp has an invalid minute or second.")
        return (
            int((hours or "0").rstrip(":")) * 3600
            + int(minutes) * 60
            + int(seconds)
            + int(millis) / 1000
        )

    def parse(self, text: str, suffix: str) -> tuple[SubtitleCue, ...]:
        if len(text.encode("utf-8")) > PublicHTTPSClient.MAX_BYTES:
            raise GateError("Subtitle export exceeds the 1 MB limit.")
        try:
            if suffix.lower() == ".json":
                data = _BilibiliSubtitles.model_validate_json(text)
                cues = tuple(
                    SubtitleCue(start_seconds=c.start, end_seconds=c.end, text=c.content)
                    for c in data.body
                )
            elif suffix.lower() in {".srt", ".vtt"}:
                result: list[SubtitleCue] = []
                normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
                for block in re.split(r"\n\s*\n", normalized.strip()):
                    lines = block.splitlines()
                    if not lines or lines[0].startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
                        continue
                    index = 0 if "-->" in lines[0] else 1
                    if len(lines) <= index or not (match := self._TIMING.fullmatch(lines[index])):
                        raise GateError("Subtitle export contains an invalid cue timestamp.")
                    groups = match.groups()
                    start = self._seconds(groups[0], groups[1], groups[2], groups[3])
                    end = self._seconds(groups[4], groups[5], groups[6], groups[7])
                    content = unescape(re.sub(r"<[^>]*>", "", " ".join(lines[index + 1 :])))
                    result.append(SubtitleCue(start_seconds=start, end_seconds=end, text=content))
                cues = tuple(result)
            else:
                raise GateError("Supported subtitle exports are .srt, .vtt and Bilibili .json.")
            if not cues or len(cues) > 5000:
                raise GateError("Subtitle export must contain between 1 and 5000 cues.")
            return TypeAdapter(tuple[SubtitleCue, ...]).validate_python(cues)
        except ValidationError as exc:
            raise GateError("Subtitle export contains invalid cue data.") from exc
