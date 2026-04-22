"""
Appointment API — FastAPI service providing appointment management with
structured logging, Prometheus metrics, API-key authentication, and
cleanly tagged OpenAPI documentation.

Features:
- CRUD + cancellation workflow for appointments
- API-key protected endpoints using X-API-Key header
- Structured JSON access logs with request IDs
- Prometheus metrics (request count + latency histograms)
- Health, readiness, and service metadata endpoints
- In-memory datastore for development/testing
- OpenAPI tags for clean grouping in Swagger UI
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI, Form, HTTPException, Query, Request, Security
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from starlette.status import HTTP_303_SEE_OTHER

from app.auth import require_api_key


# ---- Path setup (repo-structure safe) ----
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ---- logging setup (structured JSON to stdout) ----
logger = logging.getLogger("appointment_api")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(message)s"))
logger.handlers = [_handler]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_future(dt: datetime) -> None:
    # If client sends a naive datetime, assume UTC to avoid surprises
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if dt <= _utcnow():
        raise HTTPException(
            status_code=422, detail="appointment_time must be in the future"
        )


def _log(event: dict) -> None:
    logger.info(json.dumps(event, separators=(",", ":"), default=str))


# ---- Prometheus metrics ----
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["path"]
)

# ---- OpenAPI tags ----
tags_metadata = [
    {"name": "Health", "description": "Liveness and readiness probes"},
    {"name": "Meta", "description": "Service metadata"},
    {"name": "Appointments", "description": "Appointment management APIs"},
    {"name": "Observability", "description": "Metrics and monitoring endpoints"},
    {"name": "UI", "description": "Server-rendered demo UI routes"},
    {"name": "Lab", "description": "Development-only runtime testing endpoints"},
]

# ---- FastAPI app ----
app = FastAPI(
    title="Appointment API",
    version="0.2.0",
    openapi_tags=tags_metadata,
    # NOTE: Swagger UI can be flaky with OpenAPI 3.1 in some bundled versions.
    # For maximum compatibility (and to avoid a blank /docs page), publish as OAS 3.0.3.
    openapi_version="3.0.3",
    # NOTE: This keeps the API key in Swagger UI once you click "Authorize".
    swagger_ui_parameters={"persistAuthorization": True},
)

# ---- Static assets (Demo UI CSS) ----
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---- Auth (API Key) ----
# NOTE: Use Security(...) so FastAPI auto-generates the OpenAPI security scheme
# and Swagger UI shows the "Authorize" button.
AUTH_DEPENDENCY = [Security(require_api_key)]
AUTH_RESPONSES = {
    401: {"description": "Unauthorized"},
    403: {"description": "Forbidden"},
}


# ---- models ----
class AppointmentCreate(BaseModel):
    patient_id: str = Field(min_length=1)
    patient_name: str = Field(min_length=1)
    clinic: str = Field(min_length=1)
    appointment_time: datetime


class AppointmentUpdate(BaseModel):
    patient_id: str = Field(min_length=1)
    patient_name: str = Field(min_length=1)
    clinic: str = Field(min_length=1)
    appointment_time: datetime


class Appointment(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    clinic: str
    appointment_time: datetime
    status: Literal["BOOKED", "CANCELLED"] = "BOOKED"


_DB: List[Appointment] = []

# Startup probe state
_STARTUP_COMPLETE = False


def _find_index_by_id(appt_id: str) -> int:
    for i, a in enumerate(_DB):
        if a.id == appt_id:
            return i
    return -1


def _get_by_id_or_404(appt_id: str) -> Appointment:
    idx = _find_index_by_id(appt_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _DB[idx]


# ---- middleware: request id + structured access logs ----
@app.middleware("http")
async def access_log(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    start = time.time()

    try:
        response = await call_next(request)
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        _log(
            {
                "ts": _utcnow().isoformat(),
                "level": "ERROR",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "status": 500,
                "latency_ms": elapsed_ms,
                "error": str(e),
            }
        )
        raise

    elapsed_ms = int((time.time() - start) * 1000)
    _log(
        {
            "ts": _utcnow().isoformat(),
            "level": "INFO",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query),
            "status": response.status_code,
            "latency_ms": elapsed_ms,
        }
    )
    response.headers["x-request-id"] = request_id
    return response


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    REQUEST_COUNT.labels(
        method=request.method, path=request.url.path, status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(path=request.url.path).observe(duration)

    return response


# ---- startup lifecycle ----
@app.on_event("startup")
async def on_startup():
    """
    Application startup hook.

    Future use:
    - initialize database connections
    - warm caches
    - verify external dependencies
    """
    global _STARTUP_COMPLETE
    _STARTUP_COMPLETE = True


# ---- endpoints ----
@app.get("/healthz", tags=["Health"])
def healthz():
    return {"status": "ok"}


@app.get("/readyz", tags=["Health"])
def readyz():
    return {"status": "ready"}


@app.get("/startupz", tags=["Health"])
def startupz():
    """
    Startup probe endpoint.

    Used by Kubernetes startupProbe to determine whether the application
    has completed startup successfully.
    """
    if not _STARTUP_COMPLETE:
        raise HTTPException(status_code=503, detail="Application startup not complete")
    return {"status": "started"}


@app.get("/info", tags=["Meta"])
def info():
    return {"service": "appointment-api", "version": "0.2.0"}


@app.get(
    "/api/v1/appointments",
    response_model=List[Appointment],
    tags=["Appointments"],
    dependencies=AUTH_DEPENDENCY,
    responses=AUTH_RESPONSES,
)
def list_appointments(
    patient_id: Optional[str] = None,
    status: Optional[Literal["BOOKED", "CANCELLED"]] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    items = _DB
    if patient_id:
        items = [a for a in items if a.patient_id == patient_id]
    if status:
        items = [a for a in items if a.status == status]

    start = (page - 1) * size
    end = start + size
    return items[start:end]


@app.post(
    "/api/v1/appointments",
    response_model=Appointment,
    status_code=201,
    tags=["Appointments"],
    dependencies=AUTH_DEPENDENCY,
    responses=AUTH_RESPONSES,
)
def create_appointment(payload: AppointmentCreate):
    _require_future(payload.appointment_time)
    appt = Appointment(
        id=str(uuid4()),
        patient_id=payload.patient_id,
        patient_name=payload.patient_name,
        clinic=payload.clinic,
        appointment_time=payload.appointment_time,
        status="BOOKED",
    )
    _DB.append(appt)
    return appt


@app.get(
    "/api/v1/appointments/{appointment_id}",
    response_model=Appointment,
    tags=["Appointments"],
    dependencies=AUTH_DEPENDENCY,
    responses=AUTH_RESPONSES,
)
def get_appointment(appointment_id: str):
    return _get_by_id_or_404(appointment_id)


# PUT update (full replacement)
@app.put(
    "/api/v1/appointments/{appointment_id}",
    response_model=Appointment,
    tags=["Appointments"],
    dependencies=AUTH_DEPENDENCY,
    responses=AUTH_RESPONSES,
)
def update_appointment(appointment_id: str, payload: AppointmentUpdate):
    _require_future(payload.appointment_time)
    idx = _find_index_by_id(appointment_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail="Appointment not found")

    existing = _DB[idx]
    updated = Appointment(
        id=existing.id,
        patient_id=payload.patient_id,
        patient_name=payload.patient_name,
        clinic=payload.clinic,
        appointment_time=payload.appointment_time,
        status=existing.status,  # keep status unless cancelled via PATCH endpoint
    )
    _DB[idx] = updated
    return updated


# Cancel (state transition)
@app.patch(
    "/api/v1/appointments/{appointment_id}/cancel",
    response_model=Appointment,
    tags=["Appointments"],
    dependencies=AUTH_DEPENDENCY,
    responses=AUTH_RESPONSES,
)
def cancel_appointment(appointment_id: str):
    idx = _find_index_by_id(appointment_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appt = _DB[idx]
    if appt.status == "CANCELLED":
        return appt  # idempotent

    appt.status = "CANCELLED"
    _DB[idx] = appt
    return appt


@app.delete(
    "/api/v1/appointments/{appointment_id}",
    status_code=204,
    tags=["Appointments"],
    dependencies=AUTH_DEPENDENCY,
    responses=AUTH_RESPONSES,
)
def delete_appointment(appointment_id: str):
    idx = _find_index_by_id(appointment_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail="Appointment not found")
    _DB.pop(idx)
    return


@app.get(
    "/metrics",
    tags=["Observability"],
    dependencies=AUTH_DEPENDENCY,
    responses=AUTH_RESPONSES,
)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---- OpenAPI customization (safe) ----
# NOTE:
# - We do NOT force a global "security" requirement here. We let per-route dependencies drive security.
# - This prevents Swagger UI from breaking and keeps /docs public but showing "Authorize" when needed.
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        tags=tags_metadata,
    )

    # Ensure components exists
    openapi_schema.setdefault("components", {})
    openapi_schema["components"].setdefault("securitySchemes", {})

    # Ensure our API key scheme exists (in case FastAPI didn't add it for any reason)
    openapi_schema["components"]["securitySchemes"].setdefault(
        "APIKeyHeader",
        {"type": "apiKey", "in": "header", "name": "X-API-Key"},
    )

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# =============================================================================
# Demo UI (Server-rendered HTML)
# =============================================================================
# Purpose:
# - Provide a lightweight "Demo UI" for humans to interact with the service
#   without introducing a separate frontend stack (no React/Node/build step).
#
# Design:
# - UI routes are intentionally NOT API-key protected.
# - API routes (/api/v1/*) remain protected via X-API-Key.
# - UI handlers reuse the same validation + data layer used by the API.
#
# Notes:
# - Templates live in ./templates
# - Static assets (CSS) live in ./static and are served at /static/*
# =============================================================================


@app.get("/ui", response_class=HTMLResponse, tags=["UI"])
def ui_home(request: Request):
    """
    Demo UI landing page (dashboard).
    Shows basic service info + quick links to actions and docs.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "service": "appointment-api",
            "version": app.version,
            "count": len(_DB),
            "title": "Dashboard — Demo UI",
        },
    )


@app.get("/ui/appointments", response_class=HTMLResponse, tags=["UI"])
def ui_list_appointments(
    request: Request,
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
):
    # Normalize empty inputs from HTML forms
    patient_id = (patient_id or "").strip() or None
    status = (status or "").strip() or None

    # Validate allowed status values if provided
    if status and status not in {"BOOKED", "CANCELLED"}:
        raise HTTPException(
            status_code=422, detail="status must be BOOKED or CANCELLED"
        )

    items = _DB
    if patient_id:
        items = [a for a in items if a.patient_id == patient_id]
    if status:
        items = [a for a in items if a.status == status]

    return templates.TemplateResponse(
        "appointments.html",
        {
            "request": request,
            "items": items,
            "patient_id": patient_id or "",
            "status": status or "",
            "title": "Appointments — Demo UI",
        },
    )


@app.get("/ui/appointments/new", response_class=HTMLResponse, tags=["UI"])
def ui_new_appointment(request: Request):
    """
    Demo UI form page for creating a new appointment.
    """
    return templates.TemplateResponse(
        "new_appointment.html",
        {"request": request, "title": "New Appointment — Demo UI"},
    )


@app.post("/ui/appointments", tags=["UI"])
def ui_create_appointment(
    patient_id: str = Form(..., min_length=1),
    patient_name: str = Form(..., min_length=1),
    clinic: str = Form(..., min_length=1),
    appointment_time: str = Form(...),
):
    try:
        ts = appointment_time.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="appointment_time must be ISO8601, e.g. 2026-03-01T12:00:00Z",
        )

    _require_future(dt)

    appt = Appointment(
        id=str(uuid4()),
        patient_id=patient_id,
        patient_name=patient_name,
        clinic=clinic,
        appointment_time=dt,
        status="BOOKED",
    )
    _DB.append(appt)

    return RedirectResponse(url="/ui/appointments", status_code=HTTP_303_SEE_OTHER)


@app.post("/ui/appointments/{appointment_id}/cancel", tags=["UI"])
def ui_cancel_appointment(appointment_id: str):
    """
    Demo UI action: cancel an appointment (idempotent).
    Reuses the existing API handler logic.
    """
    cancel_appointment(appointment_id)
    return RedirectResponse(url="/ui/appointments", status_code=HTTP_303_SEE_OTHER)


@app.post("/ui/appointments/{appointment_id}/delete", tags=["UI"])
def ui_delete_appointment(appointment_id: str):
    """
    Demo UI action: delete an appointment.
    Reuses the existing API handler logic.
    """
    delete_appointment(appointment_id)
    return RedirectResponse(url="/ui/appointments", status_code=HTTP_303_SEE_OTHER)


# ---- ######################################### ----
# ---- ######################################### ----


# ---- Lab / runtime testing feature flag ----
def _lab_endpoints_enabled() -> bool:
    return os.getenv("ENABLE_LAB_ENDPOINTS", "false").lower() == "true"


# ---- Lab endpoints (dev-only learning routes) ----
# NOTE:
# These routes are intentionally for runtime testing and troubleshooting drills.
# They should only be enabled in development-style environments by setting:
# ENABLE_LAB_ENDPOINTS=true


@app.get("/lab/slow", tags=["Lab"])
def lab_slow(seconds: int = Query(5, ge=1, le=15)):
    # Guardrail: keep this route disabled unless explicitly enabled
    if not _lab_endpoints_enabled():
        raise HTTPException(status_code=404, detail="Not found")

    # Simulate bounded application latency
    time.sleep(seconds)

    return {
        "status": "ok",
        "mode": "slow",
        "slept_seconds": seconds,
    }


@app.get("/lab/fail", tags=["Lab"])
def lab_fail():
    # Guardrail: keep this route disabled unless explicitly enabled
    if not _lab_endpoints_enabled():
        raise HTTPException(status_code=404, detail="Not found")

    # Simulate a deliberate application failure
    raise HTTPException(status_code=500, detail="Deliberate lab failure")
