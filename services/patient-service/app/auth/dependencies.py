
# =============================================================================
# FastAPI authentication dependencies for patient-service
# =============================================================================
# Maps typed auth exceptions from api_key.py to HTTP responses.
# Import require_api_key and use with FastAPI Depends() to protect endpoints.
#
# Usage — protect a single endpoint:
#     from app.auth.dependencies import require_api_key
#     from fastapi import Depends
#
#     @router.get("/patients", dependencies=[Depends(require_api_key)])
#     async def list_patients(): ...
#
# Usage — protect an entire router:
#     router = APIRouter(dependencies=[Depends(require_api_key)])
#
# Usage — access the validated key value:
#     @router.post("/patients")
#     async def create_patient(api_key: str = Depends(require_api_key)): ...
#
# When JWT or OAuth2 arrives, add new dependency functions here.
# Existing endpoints using require_api_key are unaffected.
# =============================================================================

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.auth.api_key import (
    InvalidApiKeyError,
    MissingApiKeyError,
    validate_api_key,
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """
    FastAPI dependency — enforces X-API-Key authentication.

    Returns the validated key string on success.
    Raises 401 Unauthorized if no key is provided.
    Raises 403 Forbidden if the key is present but invalid.

    Add as Depends(require_api_key) to any protected endpoint or router.
    """
    try:
        return validate_api_key(api_key)
    except MissingApiKeyError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "API-Key"},
        )
    except InvalidApiKeyError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )