
# =============================================================================
# API key validation logic for patient-service
# =============================================================================
# Validates the API key value in isolation from FastAPI concerns.
# Raises typed exceptions — never HTTPException.
# HTTP status mapping belongs in dependencies.py, not here.
#
# This separation means:
# - validate_api_key() can be tested without a FastAPI test client
# - When JWT or OAuth2 arrives, this file gets a sibling (jwt.py)
#   and dependencies.py routes to the correct validator per endpoint
# =============================================================================

import secrets

from app.core.config import settings


class MissingApiKeyError(Exception):
    """Raised when the X-API-Key header is absent or empty."""

class InvalidApiKeyError(Exception):
    """Raised when the X-API-Key header is present but does not match."""

def validate_api_key(api_key: str | None) -> str:
    """
    Validate the provided API key against PATIENT_SERVICE_API_KEY.

    Uses secrets.compare_digest for timing-safe comparison.
    Timing-safe comparison prevents attackers from inferring
    key validity from differences in response time.

    Args:
        api_key: Value from the X-API-Key header, or None if absent.

    Returns:
        The validated API key string on success.

    Raises:
        MissingApiKeyError: No key was provided.
        InvalidApiKeyError: Key was provided but does not match.
    """
    if not api_key:
        raise MissingApiKeyError("X-API-Key header is missing or empty")

    if not secrets.compare_digest(api_key, settings.patient_service_api_key):
        raise InvalidApiKeyError("X-API-Key value does not match")

    return api_key