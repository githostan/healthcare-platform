from fastapi import APIRouter

from .health import router as health_router
from .meta import router as meta_router
from .metrics import router as metrics_router
from .patients import router as patients_router

router = APIRouter()

router.include_router(health_router)  # /healthz, /readyz, /startupz
router.include_router(meta_router)  # /info
router.include_router(metrics_router)  # /metrics
router.include_router(patients_router)  # /patients — prefix comes from main.py
