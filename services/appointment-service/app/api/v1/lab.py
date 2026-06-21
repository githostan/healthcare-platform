# =============================================================================
# Lab / runtime testing endpoints (dev-only)
# =============================================================================
# NOTE (Purpose):
# - Intentional routes for runtime testing and troubleshooting drills
#   (simulated latency, simulated failure).
# - Gated by settings.enable_lab_endpoints (ENABLE_LAB_ENDPOINTS env var) —
#   sourced from Pydantic Settings rather than os.getenv directly, so the
#   flag participates in the same validated configuration as everything
#   else in app/core/config.py.
# - Returns 404 (not 403) when disabled, so the existence of these routes
#   is not revealed in environments where they're off.

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings

router = APIRouter(prefix="/lab", tags=["Lab"])


def _require_lab_enabled() -> None:
    if not settings.enable_lab_endpoints:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/slow")
def lab_slow(seconds: int = Query(5, ge=1, le=15)) -> dict[str, str | int]:
    _require_lab_enabled()
    time.sleep(seconds)
    return {"status": "ok", "mode": "slow", "slept_seconds": seconds}


@router.get("/fail")
def lab_fail() -> None:
    _require_lab_enabled()
    raise HTTPException(status_code=500, detail="Deliberate lab failure")
