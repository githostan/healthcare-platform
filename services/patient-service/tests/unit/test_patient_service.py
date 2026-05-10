
"""
Unit tests for PatientService.

Purpose:
- Test business logic without HTTP routes
- Validate duplicate detection, soft delete, and eligibility rules
"""

import logging

import pytest
from fastapi import HTTPException

from app.repositories.patient_repository import InMemoryPatientRepository
from app.schemas.patient import PatientCreate, PatientStatusUpdate
from app.services.patient_service import PatientService
from app.utils.nhs import generate_valid_nhs_number


@pytest.fixture
def service() -> PatientService:
    repository = InMemoryPatientRepository()
    logger = logging.getLogger("test_patient_service")
    return PatientService(repository=repository, logger=logger)


@pytest.fixture
def valid_create_payload() -> PatientCreate:
    return PatientCreate(
        nhs_number=generate_valid_nhs_number(),
        first_name="Service",
        last_name="Test",
        date_of_birth="1990-01-01",
        gender="MALE",
        registered_practice_code="L83120",
        status="ACTIVE",
    )


def test_create_patient_returns_patient_out(service, valid_create_payload):
    result = service.create_patient(
        valid_create_payload,
        request_id="req-1",
        correlation_id="corr-1",
        api_key="test-key",
    )

    assert result.first_name == "Service"
    assert result.status == "ACTIVE"
    assert result.id is not None


def test_create_duplicate_nhs_raises_409(service, valid_create_payload):
    service.create_patient(
        valid_create_payload,
        request_id="req-1",
        correlation_id="corr-1",
        api_key="test-key",
    )

    with pytest.raises(HTTPException) as exc:
        service.create_patient(
            valid_create_payload,
            request_id="req-2",
            correlation_id="corr-2",
            api_key="test-key",
        )

    assert exc.value.status_code == 409


def test_get_nonexistent_patient_raises_404(service):
    with pytest.raises(HTTPException) as exc:
        service.get_patient("nonexistent-id")

    assert exc.value.status_code == 404


def test_soft_delete_sets_patient_inactive(service, valid_create_payload):
    created = service.create_patient(
        valid_create_payload,
        request_id="req-1",
        correlation_id="corr-1",
        api_key="test-key",
    )

    service.soft_delete(
        created.id,
        request_id="req-2",
        correlation_id="corr-2",
        api_key="test-key",
    )

    eligibility = service.get_eligibility(created.id)

    assert eligibility.eligible_for_booking is False


def test_update_status_sets_patient_inactive(service, valid_create_payload):
    created = service.create_patient(
        valid_create_payload,
        request_id="req-1",
        correlation_id="corr-1",
        api_key="test-key",
    )

    updated = service.update_status(
        created.id,
        PatientStatusUpdate(status="INACTIVE"),
        request_id="req-2",
        correlation_id="corr-2",
        api_key="test-key",
    )

    assert updated.status == "INACTIVE"


def test_eligibility_returns_false_for_unknown_patient(service):
    result = service.get_eligibility("ghost-id")

    assert result.exists is False
    assert result.eligible_for_booking is False


def test_list_excludes_inactive_by_default(service, valid_create_payload):
    created = service.create_patient(
        valid_create_payload,
        request_id="req-1",
        correlation_id="corr-1",
        api_key="test-key",
    )

    service.update_status(
        created.id,
        PatientStatusUpdate(status="INACTIVE"),
        request_id="req-2",
        correlation_id="corr-2",
        api_key="test-key",
    )

    result = service.list_patients(
        status=None,
        registered_practice_code=None,
        include_inactive=False,
        page=1,
        size=20,
    )

    assert result.items == []