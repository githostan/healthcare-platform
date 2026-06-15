
# =============================================================================
# Service metadata endpoint (version, identity, build information)
# =============================================================================
# NOTE (Purpose):
# - Exposes lightweight metadata about the running patient-service instance.
# - Used for debugging, observability, CI/CD verification, and platform tooling.
# - This endpoint is NOT a health probe; it simply reports static service info.
# - Includes OTel configuration state, k8s context, and feature flag status
#   so operators can verify deployment configuration without kubectl exec.
# - Avoids exposing sensitive operational throttling values such as rate limits.

import platform
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from opentelemetry import trace
from opentelemetry.trace import SpanKind

from app.core.config import settings

router = APIRouter(tags=["Meta"])
tracer = trace.get_tracer(__name__)

# Recorded at module load — used to compute uptime in /info.
# NOTE:
# - This is acceptable for the current service shape.
# - When app startup metadata is centralised, prefer app.state.started_at
#   from the FastAPI lifespan handler.
_start_time = time.time()


@router.get("/info")
def info() -> dict[str, Any]:
    with tracer.start_as_current_span(
        "service.info",
        kind=SpanKind.INTERNAL,
    ):
        return {
            "service": settings.service_name,
            "version": settings.service_version,
            "environment": settings.environment,
            "uptime_seconds": round(time.time() - _start_time, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "observability": {
                "otel_enabled": settings.otel_enabled,
                "otel_endpoint": settings.otel_exporter_otlp_endpoint or "console",
                "otel_protocol": settings.otel_exporter_protocol,
                "otel_sampling_ratio": settings.otel_sampling_ratio,
            },
            "k8s": {
                "namespace": settings.k8s_namespace,
                "pod": settings.k8s_pod_name,
                "node": settings.k8s_node_name,
            },
            "features": {
                "seed_data": settings.enable_seed_data,
            },
            "runtime": {
                "python_version": platform.python_version(),
            },
        }