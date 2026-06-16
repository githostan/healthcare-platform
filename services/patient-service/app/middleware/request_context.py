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
#
# Implementation note:
#   Uses pure ASGI middleware instead of BaseHTTPMiddleware.
#   BaseHTTPMiddleware breaks OTel context propagation across the call_next
#   boundary — the OTel span context is lost by the time request_complete
#   is logged. Pure ASGI middleware preserves the context throughout the
#   entire request lifecycle, giving real trace_id and span_id in all logs.

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.datastructures import MutableHeaders

from app.core.config import settings
from app.utils.security import fingerprint_api_key

from app.metrics.collector import REQUEST_COUNT, REQUEST_LATENCY, rate_limit_hits_total


class RequestContextMiddleware:
    """
    Pure ASGI middleware for request context injection and observability.

    Does not extend BaseHTTPMiddleware — pure ASGI __call__ preserves
    the OTel context across the entire request lifecycle so trace_id
    and span_id are real and non-zero in all log lines including
    request_complete.
    """

    EXEMPT_PATHS = {"/healthz", "/readyz", "/startupz", "/info", "/metrics"}

    def __init__(self, app: ASGIApp, logger: logging.Logger) -> None:
        self.app = app
        self.logger = logger
        self.requests_by_key: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)
        path = request.url.path

        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())

        # Inject into request state for route handlers to access
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        api_key = request.headers.get("X-API-Key", "")
        now = time.time()

        # Rate limiting — skip exempt paths
        if api_key and path not in self.EXEMPT_PATHS:
            window = self.requests_by_key[api_key]
            while window and now - window[0] > 60:
                window.popleft()

            if len(window) >= settings.rate_limit_per_minute:
                REQUEST_COUNT.labels(
                    method=request.method,
                    path=path,
                    status="429",
                ).inc()
                REQUEST_LATENCY.labels(path=path).observe(0)
                rate_limit_hits_total.inc()

                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={
                        "X-Request-ID": request_id,
                        "X-Correlation-ID": correlation_id,
                    },
                )
                await response(scope, receive, send)
                return

            window.append(now)

        start = time.time()
        status_code = 500

        async def send_with_headers(message) -> None:
            """
            Intercept http.response.start to inject response headers
            and capture the status code for metrics and logging.

            Uses MutableHeaders (Starlette-native) instead of raw dict
            to correctly handle duplicate headers including Set-Cookie.
            """
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # Inject MutableHeaders
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["X-Correlation-ID"] = correlation_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            elapsed = time.time() - start
            REQUEST_COUNT.labels(
                method=request.method,
                path=path,
                status="500",
            ).inc()
            REQUEST_LATENCY.labels(path=path).observe(elapsed)
            self.logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": path,
                    "status": 500,
                    "latency_ms": int(elapsed * 1000),
                },
            )
            raise

        elapsed = time.time() - start

        REQUEST_COUNT.labels(
            method=request.method,
            path=path,
            status=str(status_code),
        ).inc()
        REQUEST_LATENCY.labels(path=path).observe(elapsed)

        self.logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "method": request.method,
                "path": path,
                "status": status_code,
                "latency_ms": int(elapsed * 1000),
                "api_key_fingerprint": fingerprint_api_key(api_key),
            },
        )
