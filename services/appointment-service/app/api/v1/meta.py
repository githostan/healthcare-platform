# =============================================================================
# Service metadata route
# =============================================================================
# NOTE (Purpose):
# - Exposes basic service identity information. No authentication required.
# - Sourced from app/core/config.py's Settings rather than hardcoded
#   strings, so version/environment stay consistent with deployment config.

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["Meta"])


@router.get("/info")
def info() -> dict[str, str]:
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "environment": settings.environment,
    }
