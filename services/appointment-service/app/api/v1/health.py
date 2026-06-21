# =============================================================================
# Health and readiness probe routes
# =============================================================================
# NOTE (Purpose):
# - Liveness, readiness, and startup probes for Kubernetes.
# - No authentication — these must be reachable by the kubelet without
#   needing the service API key.
# - Startup state is tracked via app.state.startup_complete, set in
#   main.py's lifespan context manager (replaces the old module-level
#   _STARTUP_COMPLETE global).

from __future__ import annotations

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
    """
    Startup probe endpoint. Used by Kubernetes startupProbe to determine
    whether the application has completed startup successfully.
    """
    if not getattr(request.app.state, "startup_complete", False):
        raise HTTPException(status_code=503, detail="Application startup not complete")
    return {"status": "started"}
