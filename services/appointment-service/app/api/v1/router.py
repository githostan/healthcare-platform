# =============================================================================
# API v1 router aggregation
# =============================================================================
# NOTE (Purpose):
# - Combines all app/api/v1/ route modules into a single router, included
#   once in main.py via app.include_router(api_router).
# - Centralising aggregation here keeps main.py free of per-route imports.

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import appointments, health, lab, meta, metrics

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(meta.router)
api_router.include_router(appointments.router)
api_router.include_router(metrics.router)
api_router.include_router(lab.router)
