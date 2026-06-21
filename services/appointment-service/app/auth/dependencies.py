# =============================================================================
# FastAPI auth dependency — maps domain exceptions to HTTP responses
# =============================================================================
# NOTE (Purpose):
# - Wraps app/auth/api_key.py's validate_api_key() as a FastAPI Security
#   dependency, translating MissingApiKeyError -> 401 and
#   InvalidApiKeyError -> 403.
# - This is the only place in the auth flow that imports fastapi.HTTPException
#   — the validation logic itself stays framework-independent.
# - Returns the validated API key (not just None) so route handlers can
#   pass it through to the service layer for audit log fingerprinting.
#   Routes that only need protection, not the key itself, can still use
#   dependencies=[Security(require_api_key)] and discard the return value.

from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.auth.api_key import (
    InvalidApiKeyError,
    MissingApiKeyError,
    validate_api_key,
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(api_key_header)) -> str:
    try:
        validate_api_key(api_key)
    except MissingApiKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    except InvalidApiKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    # validate_api_key raises on any falsy/invalid api_key, so reaching
    # this point guarantees api_key is a non-empty string.
    assert api_key is not None
    return api_key
