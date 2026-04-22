import os
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Security(API_KEY_HEADER)) -> None:
    expected = os.getenv("APPOINTMENT_API_KEY", "dev-secret-key")

    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    if api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")
