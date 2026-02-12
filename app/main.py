
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

from fastapi import FastAPI, HTTPException, Query, Request, Security
from fastapi.responses import Response
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from uuid import uuid4
from datetime import datetime, timezone
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
import json
import logging

from app.auth import require_api_key


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
        raise HTTPException(status_code=422, detail="appointment_time must be in the future")


def _log(event: dict) -> None:
    logger.info(json.dumps(event, separators=(",", ":"), default=str))


# ---- Prometheus metrics ----
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["path"]
)

# ---- OpenAPI tags ----
tags_metadata = [
    {"name": "Health", "description": "Liveness and readiness probes"},
    {"name": "Meta", "description": "Service metadata"},
    {"name": "Appointments", "description": "Appointment management APIs"},
    {"name": "Observability", "description": "Metrics and monitoring endpoints"},
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
    clinic: str = Field(min_length=1)
    appointment_time: datetime


class AppointmentUpdate(BaseModel):
    patient_id: str = Field(min_length=1)
    clinic: str = Field(min_length=1)
    appointment_time: datetime


class Appointment(BaseModel):
    id: str
    patient_id: str
    clinic: str
    appointment_time: datetime
    status: Literal["BOOKED", "CANCELLED"] = "BOOKED"


_DB: List[Appointment] = []


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
        method=request.method,
        path=request.url.path,
        status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(
        path=request.url.path
    ).observe(duration)

    return response


# ---- endpoints ----
@app.get("/healthz", tags=["Health"])
def healthz():
    return {"status": "ok"}


@app.get("/readyz", tags=["Health"])
def readyz():
    return {"status": "ready"}


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
