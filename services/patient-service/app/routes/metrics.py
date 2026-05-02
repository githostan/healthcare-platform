
# =============================================================================
# Prometheus metrics endpoint (service-level observability)
# =============================================================================
# NOTE (Purpose):
# - Exposes the `/metrics` endpoint used by Prometheus to scrape runtime metrics.
# - Returns the latest metrics snapshot in the Prometheus text exposition format.
# - Protected by API‑key authentication to prevent unauthorised scraping.
# - Integrates with FastAPI instrumentation, custom counters/histograms, and
#   any metrics registered via `prometheus_client`.
# - Forms the core observability surface for dashboards, alerts, and SLO tracking.

from fastapi import APIRouter, Security
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.auth import require_api_key

router = APIRouter(tags=["Observability"])


@router.get("/metrics", dependencies=[Security(require_api_key)])
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

