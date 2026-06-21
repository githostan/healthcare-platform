# =============================================================================
# Request context middleware — pure ASGI implementation
# =============================================================================
# NOTE (Purpose):
# - Single middleware combining: request ID / correlation ID injection,
#   structured access logging, RED metric recording (count + latency),
#   and sliding-window rate limiting.
# - Implemented as pure ASGI (not BaseHTTPMiddleware) to preserve OTel
#   context propagation end-to-end and avoid buffering streaming responses
#   — matches patient-service's middleware architecture decision.
# - Uses MutableHeaders rather than raw dict manipulation, so Set-Cookie
#   and other duplicate-capable headers are handled safely.
# - Rate limiting is IP-based, not API-key-based. appointment-service
#   currently has a single shared service API key — keying the limiter by
#   that key would collapse all legitimate callers into one shared bucket,
#   which is strictly worse than IP-based limiting for the current
#   single-key security model. Revisit if/when per-client API keys exist.
# - Rate limiting state is in-memory per-process (sliding window keyed by
#   client IP). Acceptable for a single-replica dev deployment; would need
#   a shared store (Redis) for multi-replica production use.

from __future__ import annotations

import time
from collections import defaultdict, deque
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.logging_config import get_logger
from app.metrics.collector import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    rate_limit_hits_total,
)

logger = get_logger("appointment_api.middleware")


class RequestContextMiddleware:
    """
    Pure ASGI middleware. Wraps each HTTP request to:
      1. Assign/propagate a request ID and correlation ID.
      2. Enforce a sliding-window rate limit per client IP.
      3. Record RED metrics (request count, latency).
      4. Emit a structured 'request_complete' access log.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._window_seconds = 60
        self._limit = settings.rate_limit_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, scope: Scope) -> str:
        client = scope.get("client")
        return f"ip:{client[0]}" if client else "ip:unknown"

    def _is_rate_limited(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self._window_seconds
        hits = self._hits[key]

        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= self._limit:
            return True

        hits.append(now)
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }

        request_id = headers.get("x-request-id") or str(uuid4())
        correlation_id = headers.get("x-correlation-id") or request_id
        method = scope["method"]
        path = scope["path"]

        # Make IDs available to downstream route handlers via request.scope,
        # so app/api/v1/appointments.py reads the same IDs this middleware
        # generated, rather than each layer generating independent UUIDs.
        scope["request_id"] = request_id
        scope["correlation_id"] = correlation_id

        client_key = self._client_key(scope)
        if self._is_rate_limited(client_key):
            rate_limit_hits_total.inc()
            await self._send_429(send, request_id, correlation_id)
            logger.warning(
                "rate_limit_exceeded",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "method": method,
                    "path": path,
                    "client_key": client_key,
                },
            )
            return

        start = time.monotonic()
        status_code_holder = {"status": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code_holder["status"] = message["status"]
                headers_out = MutableHeaders(scope=message)
                headers_out.append("x-request-id", request_id)
                headers_out.append("x-correlation-id", correlation_id)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            elapsed = time.monotonic() - start
            REQUEST_COUNT.labels(method=method, path=path, status=500).inc()
            REQUEST_LATENCY.labels(path=path).observe(elapsed)
            logger.error(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "method": method,
                    "path": path,
                    "status": 500,
                    "latency_ms": int(elapsed * 1000),
                    "error": str(exc),
                },
            )
            raise
        else:
            elapsed = time.monotonic() - start
            status = status_code_holder["status"]
            REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
            REQUEST_LATENCY.labels(path=path).observe(elapsed)
            logger.info(
                "request_complete",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "method": method,
                    "path": path,
                    "status": status,
                    "latency_ms": int(elapsed * 1000),
                },
            )

    async def _send_429(self, send: Send, request_id: str, correlation_id: str) -> None:
        body = b'{"detail":"Rate limit exceeded"}'
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"x-request-id", request_id.encode("latin-1")),
                    (b"x-correlation-id", correlation_id.encode("latin-1")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
