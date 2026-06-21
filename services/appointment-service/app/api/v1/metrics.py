# =============================================================================
# Prometheus metrics endpoint
# =============================================================================
# NOTE (Purpose):
# - Exposes /metrics in Prometheus exposition format for scraping.
# - Requires authentication, matching the original monolith's behaviour —
#   the metrics endpoint is not publicly exposed.

from __future__ import annotations

from fastapi import APIRouter, Response, Security
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.auth.dependencies import require_api_key

router = APIRouter(tags=["Observability"])

AUTH_RESPONSES = {
    401: {"description": "Unauthorized"},
    403: {"description": "Forbidden"},
}


@router.get(
    "/metrics", responses=AUTH_RESPONSES, dependencies=[Security(require_api_key)]
)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
