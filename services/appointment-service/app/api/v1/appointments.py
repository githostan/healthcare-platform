# =============================================================================
# Appointment CRUD routes
# =============================================================================
# NOTE (Purpose):
# - Thin HTTP layer over AppointmentService. Translates domain exceptions
#   (AppointmentNotFoundError -> 404, AppointmentValidationError -> 422)
#   into HTTP responses — the service layer itself raises neither
#   HTTPException nor any FastAPI-specific type.
# - AppointmentService instance is retrieved from app.state, set in
#   main.py's lifespan context manager (per-app-instance, not a
#   module-level singleton — keeps tests isolated).
# - api_key: str = Security(require_api_key) — not just a bare dependency —
#   because the service layer's audit logging needs the validated key for
#   fingerprinting (see app/auth/dependencies.py NOTE).
# - _request_context() prefers request.scope["request_id"]/["correlation_id"],
#   populated by RequestContextMiddleware (Step 9), falling back to headers
#   only if scope values are absent. This ensures the audit log ID matches
#   the access log ID for the same request, rather than each layer
#   generating an independent UUID.

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, Security
from fastapi import status as http_status

from app.auth.dependencies import require_api_key
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentOut,
    AppointmentStatus,
    AppointmentUpdate,
)
from app.services.appointment_service import (
    AppointmentNotFoundError,
    AppointmentService,
    AppointmentValidationError,
)

router = APIRouter(prefix="/api/v1/appointments", tags=["Appointments"])

AUTH_RESPONSES = {
    401: {"description": "Unauthorized"},
    403: {"description": "Forbidden"},
}


def _get_service(request: Request) -> AppointmentService:
    return request.app.state.appointment_service


def _request_context(request: Request) -> tuple[str, str]:
    request_id = str(
        request.scope.get("request_id")
        or request.headers.get("x-request-id")
        or uuid4()
    )
    correlation_id = str(
        request.scope.get("correlation_id")
        or request.headers.get("x-correlation-id")
        or request_id
    )
    return request_id, correlation_id


@router.get("", response_model=AppointmentListResponse, responses=AUTH_RESPONSES)
def list_appointments(
    request: Request,
    patient_id: str | None = None,
    status: AppointmentStatus | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    api_key: str = Security(require_api_key),
) -> AppointmentListResponse:
    service = _get_service(request)
    return service.list_appointments(
        patient_id=patient_id, status=status, page=page, size=size
    )


@router.post(
    "",
    response_model=AppointmentOut,
    status_code=http_status.HTTP_201_CREATED,
    responses=AUTH_RESPONSES,
)
def create_appointment(
    request: Request,
    payload: AppointmentCreate,
    api_key: str = Security(require_api_key),
) -> AppointmentOut:
    service = _get_service(request)
    request_id, correlation_id = _request_context(request)
    try:
        return service.create_appointment(
            payload,
            request_id=request_id,
            correlation_id=correlation_id,
            api_key=api_key,
        )
    except AppointmentValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/{appointment_id}", response_model=AppointmentOut, responses=AUTH_RESPONSES
)
def get_appointment(
    request: Request,
    appointment_id: str,
    api_key: str = Security(require_api_key),
) -> AppointmentOut:
    service = _get_service(request)
    try:
        return service.get_appointment(appointment_id)
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/{appointment_id}", response_model=AppointmentOut, responses=AUTH_RESPONSES
)
def update_appointment(
    request: Request,
    appointment_id: str,
    payload: AppointmentUpdate,
    api_key: str = Security(require_api_key),
) -> AppointmentOut:
    service = _get_service(request)
    request_id, correlation_id = _request_context(request)
    try:
        return service.update_appointment(
            appointment_id,
            payload,
            request_id=request_id,
            correlation_id=correlation_id,
            api_key=api_key,
        )
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AppointmentValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch(
    "/{appointment_id}/cancel",
    response_model=AppointmentOut,
    responses=AUTH_RESPONSES,
)
def cancel_appointment(
    request: Request,
    appointment_id: str,
    api_key: str = Security(require_api_key),
) -> AppointmentOut:
    service = _get_service(request)
    request_id, correlation_id = _request_context(request)
    try:
        return service.cancel_appointment(
            appointment_id,
            request_id=request_id,
            correlation_id=correlation_id,
            api_key=api_key,
        )
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete(
    "/{appointment_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    responses=AUTH_RESPONSES,
)
def delete_appointment(
    request: Request,
    appointment_id: str,
    api_key: str = Security(require_api_key),
) -> None:
    service = _get_service(request)
    request_id, correlation_id = _request_context(request)
    try:
        service.delete_appointment(
            appointment_id,
            request_id=request_id,
            correlation_id=correlation_id,
            api_key=api_key,
        )
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
