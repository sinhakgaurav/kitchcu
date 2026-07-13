"""Request correlation for distributed tracing (Phase 1 observability)."""

from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"
MAX_CORRELATION_ID_LEN = 128


def resolve_correlation_id(request: Request) -> str:
    """Accept client correlation ID or generate one."""
    for header in (CORRELATION_ID_HEADER, REQUEST_ID_HEADER):
        value = request.headers.get(header)
        if value:
            cleaned = value.strip()
            if cleaned and len(cleaned) <= MAX_CORRELATION_ID_LEN:
                return cleaned
    return str(uuid4())


def correlation_headers(request: Request) -> dict[str, str]:
    """Headers to forward to upstream services."""
    correlation_id = getattr(request.state, "correlation_id", None) or resolve_correlation_id(
        request
    )
    return {CORRELATION_ID_HEADER: correlation_id}


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Attach correlation ID to request state and response headers."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = resolve_correlation_id(request)
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
