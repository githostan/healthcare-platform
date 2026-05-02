
# =============================================================================
# API-key authentication dependency
# =============================================================================
# NOTE (Purpose):
# - Implements lightweight API-key authentication for internal service-to-
#   service communication using the `X-API-Key` header.
# - Validates both the presence and correctness of the API key, returning:
#       • 401 Unauthorized → when no API key is provided
#       • 403 Forbidden    → when an incorrect API key is provided
# - Uses `secrets.compare_digest` for timing-safe comparison to avoid
#   side-channel attacks and ensure secure key validation.
# - Returns the validated API key for downstream use (e.g., audit logging,
#   rate limiting, request context propagation).
# - Designed for simplicity and predictability in early-stage or internal-only
#   deployments where full OAuth/OIDC is unnecessary.

import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(api_key_header)) -> str:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "API-Key"},
        )

    if not secrets.compare_digest(api_key, settings.patient_service_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key