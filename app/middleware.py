"""Request metrics middleware."""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.telemetry.metrics import http_request_duration, http_requests_total

_SKIP_PATHS = {"/metrics", "/openapi.json", "/docs", "/redoc"}


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        endpoint = request.url.path
        method = request.method
        status = str(response.status_code)

        http_request_duration.labels(method=method, endpoint=endpoint, status_code=status).observe(elapsed)
        http_requests_total.labels(method=method, endpoint=endpoint, status_code=status).inc()

        return response
