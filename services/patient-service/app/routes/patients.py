
# =============================================================================
# Patient API routes (production-grade, service-backed implementation)
# =============================================================================
# NOTE (Purpose):
# - Exposes the full patient-service API surface including CRUD operations,
#   NHS-number lookup, pagination, status updates, soft deletion, and
#   eligibility checks.
# - Delegates all business logic to PatientService for clean separation of
#   concerns and future extensibility.
# - Enforces API key authentication and propagates request context
#   (request_id, correlation_id) for observability and audit logging.
# - Uses strongly typed Pydantic models for consistent validation and
#   response formatting across the platform.

from fastapi import APIRouter, Depends, Query, Request, Security, status

from app.auth import require_api_key
from app.config import settings
from app.schemas.patient import (
    PatientCreate,
    PatientEligibilityResponse,
    PatientListResponse,
    PatientOut,
    PatientStatus,
    PatientStatusUpdate,
    PatientUpdate,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])


def get_service(request: Request) -> PatientService:
    return request.app.state.patient_service  # type: ignore[return-value]


@router.get("", response_model=PatientListResponse, dependencies=[Security(require_api_key)])
def list_patients(
    status_filter: PatientStatus | None = Query(None, alias="status"),
    registered_practice_code: str | None = Query(None),
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    service: PatientService = Depends(get_service),
) -> PatientListResponse:
    return service.list_patients(
        status=status_filter,
        registered_practice_code=registered_practice_code,
        include_inactive=include_inactive,
        page=page,
        size=size,
    )


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    request: Request,
    payload: PatientCreate,
    api_key: str = Security(require_api_key),
    service: PatientService = Depends(get_service),
) -> PatientOut:
    return service.create_patient(
        payload,
        request_id=request.state.request_id,
        correlation_id=request.state.correlation_id,
        api_key=api_key,
    )


@router.get(
    "/by-nhs-number/{nhs_number}",
    response_model=PatientOut,
    dependencies=[Security(require_api_key)],
)
def get_by_nhs_number(
    nhs_number: str,
    service: PatientService = Depends(get_service),
) -> PatientOut:
    return service.get_by_nhs_number(nhs_number)


@router.get(
    "/{patient_id}",
    response_model=PatientOut,
    dependencies=[Security(require_api_key)],
)
def get_patient(
    patient_id: str,
    service: PatientService = Depends(get_service),
) -> PatientOut:
    return service.get_patient(patient_id)


@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: str,
    request: Request,
    payload: PatientUpdate,
    api_key: str = Security(require_api_key),
    service: PatientService = Depends(get_service),
) -> PatientOut:
    return service.update_patient(
        patient_id,
        payload,
        request_id=request.state.request_id,
        correlation_id=request.state.correlation_id,
        api_key=api_key,
    )


@router.patch("/{patient_id}/status", response_model=PatientOut)
def update_status(
    patient_id: str,
    request: Request,
    payload: PatientStatusUpdate,
    api_key: str = Security(require_api_key),
    service: PatientService = Depends(get_service),
) -> PatientOut:
    return service.update_status(
        patient_id,
        payload,
        request_id=request.state.request_id,
        correlation_id=request.state.correlation_id,
        api_key=api_key,
    )


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: str,
    request: Request,
    api_key: str = Security(require_api_key),
    service: PatientService = Depends(get_service),
) -> None:
    service.soft_delete(
        patient_id,
        request_id=request.state.request_id,
        correlation_id=request.state.correlation_id,
        api_key=api_key,
    )
    return None


@router.get(
    "/{patient_id}/eligibility",
    response_model=PatientEligibilityResponse,
    dependencies=[Security(require_api_key)],
)
def get_eligibility(
    patient_id: str,
    service: PatientService = Depends(get_service),
) -> PatientEligibilityResponse:
    return service.get_eligibility(patient_id)