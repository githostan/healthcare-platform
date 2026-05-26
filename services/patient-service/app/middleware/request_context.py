# =============================================================================
# Request context middleware
# (correlation IDs, rate limiting, Prometheus metrics, structured logging)
# =============================================================================
# NOTE (Purpose):
# - Injects per-request context into FastAPI/Starlette request state, including
#   request ID and correlation ID for distributed tracing and log correlation.
# - Applies lightweight, in-memory API-key rate limiting to protect the service
#   from abusive or accidental high-volume traffic, with health/meta endpoints
#   exempt from enforcement.
# - Records Prometheus metrics for request counts and latency, including
#   explicit tracking of 429 and 500 responses for accurate SLO/SLA monitoring.
# - Emits structured logs for both successful and failed requests, including
#   API-key fingerprints for audit and security visibility.
# - Provides a unified observability and traffic-governance layer that ensures
#   consistent behaviour across all routes in the patient-service.

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from app.config import settings
from app.utils.security import fingerprint_api_key

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["path"],
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/healthz", "/readyz", "/startupz", "/info", "/metrics"}

    def __init__(self, app: ASGIApp, logger: logging.Logger) -> None:
        super().__init__(app)
        self.logger = logger
        self.requests_by_key: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        api_key = request.headers.get("X-API-Key", "")
        now = time.time()

        if api_key and request.url.path not in self.EXEMPT_PATHS:
            window = self.requests_by_key[api_key]
            while window and now - window[0] > 60:
                window.popleft()

            if len(window) >= settings.rate_limit_per_minute:
                REQUEST_COUNT.labels(
                    method=request.method,
                    path=request.url.path,
                    status="429",
                ).inc()

                REQUEST_LATENCY.labels(path=request.url.path).observe(0)

                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={
                        "X-Request-ID": request_id,
                        "X-Correlation-ID": correlation_id,
                    },
                )

            window.append(now)

        start = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            elapsed = time.time() - start
            elapsed_ms = int(elapsed * 1000)
            status_code = 500

            REQUEST_COUNT.labels(
                method=request.method,
                path=request.url.path,
                status=str(status_code),
            ).inc()

            REQUEST_LATENCY.labels(path=request.url.path).observe(elapsed)

            self.logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "latency_ms": elapsed_ms,
                },
            )
            raise

        elapsed = time.time() - start
        elapsed_ms = int(elapsed * 1000)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id

        REQUEST_COUNT.labels(
            method=request.method,
            path=request.url.path,
            status=str(status_code),
        ).inc()

        REQUEST_LATENCY.labels(path=request.url.path).observe(elapsed)

        self.logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status": status_code,
                "latency_ms": elapsed_ms,
                "api_key_fingerprint": fingerprint_api_key(api_key),
            },
        )

        return response
