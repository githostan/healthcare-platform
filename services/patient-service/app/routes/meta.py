
# =============================================================================
# Service metadata endpoint (version, identity, build information)
# =============================================================================
# NOTE (Purpose):
# - Exposes lightweight metadata about the running patient-service instance.
# - Used for debugging, observability, CI/CD verification, and platform tooling.
# - This endpoint is NOT a health probe; it simply reports static service info.

from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["Meta"])


@router.get("/info")
def info() -> dict[str, str]:
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "environment": settings.environment,
    }