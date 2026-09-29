"""ASGI Middleware for HTTP request correlation, timing, and structured access logging."""

from __future__ import annotations

import logging
import re
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from goalcoach.infrastructure.logging.context import bind_context, reset_context

logger = logging.getLogger("apps.api.access")

_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_TRACEPARENT_PATTERN = re.compile(r"^00-([0-9a-fA-F]{32})-[0-9a-fA-F]{16}-[0-9a-fA-F]{2}$")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Intercepts HTTP requests to inject trace/request IDs, track latency, and emit access telemetry."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Resolve or generate Request ID
        supplied_req_id = request.headers.get("x-request-id", "").strip()
        request_id = supplied_req_id if _SAFE_ID_PATTERN.fullmatch(supplied_req_id) else uuid4().hex

        # 2. Resolve or generate Trace ID (W3C traceparent standard)
        traceparent = request.headers.get("traceparent", "").strip()
        trace_match = _TRACEPARENT_PATTERN.match(traceparent)
        trace_id = trace_match.group(1) if trace_match else uuid4().hex

        # 3. Bind execution context for this coroutine
        tokens = bind_context(request_id=request_id, trace_id=trace_id)

        start_time = perf_counter()
        status_code = 500
        response: Response | None = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (perf_counter() - start_time) * 1000

            # Attach response headers
            if response is not None:
                response.headers["X-Request-ID"] = request_id
                response.headers["x-request-id"] = request_id
                response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

            # Resolve route and client IP
            client_ip = request.client.host if request.client else "unknown"
            route_path = request.scope.get("root_path", "") + request.url.path

            log_level = logging.INFO
            if status_code >= 500:
                log_level = logging.ERROR
            elif status_code >= 400:
                log_level = logging.WARNING

            telemetry = {
                "http.method": request.method,
                "http.route": route_path,
                "http.status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "client_ip": client_ip,
            }

            logger.log(
                log_level,
                "HTTP %s %s %d (%.2fms)",
                request.method,
                route_path,
                status_code,
                duration_ms,
                extra={"extra": telemetry},
            )

            # Cleanly restore previous task context
            reset_context(tokens)


__all__ = ["ObservabilityMiddleware"]
