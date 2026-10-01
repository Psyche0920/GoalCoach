"""Asynchronous TypeSafe System One API boundary."""

from __future__ import annotations

import logging
from time import perf_counter

import httpx
from pydantic import ValidationError

from goalcoach.application.decisions.contracts import (
    DecisionError,
    DecisionRequest,
    DecisionResponse,
)
from goalcoach.infrastructure.config import Settings

logger = logging.getLogger(__name__)


class JevClient:
    def __init__(
        self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._settings = settings
        self._transport = transport

    @staticmethod
    def _validation_locations(exc: ValidationError, request: DecisionRequest) -> str:
        """Report schema locations without copying provider values into logs."""
        allowed = {"model", "answers", "type", "choice", "confidence", "probabilities"}
        allowed.update(request.questions)
        allowed.update(
            option for question in request.questions.values() for option in question.criteria
        )
        locations = []
        for error in exc.errors(include_input=False, include_url=False)[:8]:
            path = ".".join(
                str(part) if isinstance(part, int) or part in allowed else "<unknown>"
                for part in error["loc"]
            )
            locations.append(f"{path or 'response'}:{error['type']}")
        return ",".join(locations)

    async def decide(self, request: DecisionRequest) -> DecisionResponse:
        if not self._settings.jev_api_key:
            raise DecisionError(
                "Set GOALCOACH_JEV_API_KEY to an OpenRouter API key to enable Jev decisions"
            )
        started = perf_counter()
        status: int | None = None
        response_bytes: int | None = None
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.jev_base_url.rstrip("/") + "/",
                timeout=self._settings.jev_timeout_seconds,
                transport=self._transport,
                headers={
                    "Authorization": f"Bearer {self._settings.jev_api_key.get_secret_value()}"
                },
            ) as client:
                response = await client.post(
                    "systemone",
                    json={
                        "model": self._settings.jev_model,
                        **request.model_dump(mode="json"),
                    },
                )
                status = response.status_code
                response.raise_for_status()
                response_bytes = len(response.content)
                result = DecisionResponse.model_validate_json(response.content)
            if set(result.answers) != set(request.questions):
                raise DecisionError("Jev returned mismatched question IDs")
            for key, question in request.questions.items():
                answer = result.answers[key]
                if set(answer.probabilities) != set(question.criteria):
                    raise DecisionError("Jev returned options outside the candidate set")
            return result
        except ValidationError as exc:
            logger.warning(
                "Jev response validation failure: status=%s response_bytes=%s errors=%d fields=%s",
                status,
                response_bytes,
                exc.error_count(),
                self._validation_locations(exc, request),
            )
            raise DecisionError(f"Jev request failed (ValidationError, status={status})") from exc
        except httpx.HTTPError as exc:
            raise DecisionError(
                f"Jev request failed ({type(exc).__name__}, status={status})"
            ) from exc
        finally:
            logger.info(
                "Jev decision request: questions=%d status=%s duration_ms=%.2f",
                len(request.questions),
                status,
                (perf_counter() - started) * 1000,
            )
