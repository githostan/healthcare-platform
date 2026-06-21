# =============================================================================
# API key validation — pure logic, no FastAPI dependency
# =============================================================================
# NOTE (Purpose):
# - Validates the X-API-Key header against the configured service key
#   using a timing-safe comparison.
# - Raises typed domain exceptions (MissingApiKeyError, InvalidApiKeyError)
#   rather than HTTPException — keeps this module testable independently
#   of FastAPI, consistent with the domain-exception pattern established
#   in app/services/appointment_service.py.
# - app/auth/dependencies.py maps these exceptions to 401/403 responses.

from __future__ import annotations

from app.core.config import settings
from app.utils.security import timing_safe_compare


class MissingApiKeyError(Exception):
    """Raised when the X-API-Key header is absent from the request."""


class InvalidApiKeyError(Exception):
    """Raised when the X-API-Key header is present but does not match."""


def validate_api_key(api_key: str | None) -> None:
    """
    Validates the given API key against the configured service key.
    Raises MissingApiKeyError or InvalidApiKeyError on failure.
    Returns None on success.
    """
    if not api_key:
        raise MissingApiKeyError("X-API-Key header is required")

    if not timing_safe_compare(api_key, settings.appointment_service_api_key):
        raise InvalidApiKeyError("X-API-Key header is invalid")
