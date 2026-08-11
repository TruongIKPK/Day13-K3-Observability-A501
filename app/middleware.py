from __future__ import annotations

import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars


CORRELATION_ID_PATTERN = re.compile(r"^req-[0-9a-f]{8}$", re.IGNORECASE)


def resolve_correlation_id(candidate: str | None) -> str:
    if candidate and CORRELATION_ID_PATTERN.fullmatch(candidate):
        return candidate.lower()
    return f"req-{uuid.uuid4().hex[:8]}"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        clear_contextvars()
        correlation_id = resolve_correlation_id(request.headers.get("x-request-id"))
        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = int((time.perf_counter() - start) * 1000)
            response.headers["x-request-id"] = correlation_id
            response.headers["x-response-time-ms"] = str(duration_ms)
            return response
        finally:
            clear_contextvars()
