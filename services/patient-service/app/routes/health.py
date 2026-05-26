# =============================================================================
# Kubernetes health probe endpoints for liveness, readiness, and startup state
# =============================================================================
# NOTE:
# - Provides the operational health endpoints used by Kubernetes to determine:
#     • whether the service process is alive               (/healthz)
#     • whether the service is ready to receive traffic    (/readyz)
#     • whether startup tasks have completed               (/startupz)
# - These probes ensure safe rolling updates, controlled startup behaviour,
#   and predictable lifecycle management for patient-service.

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["Health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}


@router.get("/startupz")
def startupz(request: Request) -> dict[str, str]:
    if not getattr(request.app.state, "startup_complete", False):
        raise HTTPException(status_code=503, detail="Application startup not complete")
    return {"status": "started"}
