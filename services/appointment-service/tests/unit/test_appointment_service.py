"""
Unit tests for AppointmentService.

These exercise the service layer in isolation — no TestClient, no HTTP
layer, no FastAPI app. A bare InMemoryAppointmentRepository and a
standard logger are wired directly into AppointmentService, so these
tests verify domain logic and exception behaviour independent of how
HTTP routes eventually translate exceptions into status codes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.repositories.appointment_repository import InMemoryAppointmentRepository
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services.appointment_service import (
    AppointmentNotFoundError,
    AppointmentService,
    AppointmentValidationError,
)

REQUEST_CONTEXT = {
    "request_id": "test-request-id",
    "correlation_id": "test-correlation-id",
    "api_key": "test-appointment-api-key",
}


@pytest.fixture
def service() -> AppointmentService:
    repository = InMemoryAppointmentRepository()
    logger = logging.getLogger("test.appointment_service")
    return AppointmentService(repository=repository, logger=logger)


def _future_time() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=1)


def _past_time() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=1)


def _create_payload(**overrides) -> AppointmentCreate:
    defaults = {
        "patient_id": "12345",
        "patient_name": "Test User",
        "clinic": "Cardiology",
        "appointment_time": _future_time(),
    }
    defaults.update(overrides)
    return AppointmentCreate(**defaults)


class TestCreateAppointment:
    def test_create_succeeds_with_future_time(self, service: AppointmentService):
        result = service.create_appointment(_create_payload(), **REQUEST_CONTEXT)
        assert result.status == "BOOKED"
        assert result.patient_id == "12345"

    def test_create_raises_validation_error_for_past_time(
        self, service: AppointmentService
    ):
        payload = _create_payload(appointment_time=_past_time())
        with pytest.raises(AppointmentValidationError):
            service.create_appointment(payload, **REQUEST_CONTEXT)


class TestGetAppointment:
    def test_get_raises_not_found_for_missing_id(self, service: AppointmentService):
        with pytest.raises(AppointmentNotFoundError):
            service.get_appointment("nonexistent-id")

    def test_get_returns_existing_appointment(self, service: AppointmentService):
        created = service.create_appointment(_create_payload(), **REQUEST_CONTEXT)
        fetched = service.get_appointment(created.id)
        assert fetched.id == created.id


class TestUpdateAppointment:
    def test_update_raises_not_found_for_missing_id(self, service: AppointmentService):
        payload = AppointmentUpdate(
            patient_id="12345",
            patient_name="Test User",
            clinic="Cardiology",
            appointment_time=_future_time(),
        )
        with pytest.raises(AppointmentNotFoundError):
            service.update_appointment("nonexistent-id", payload, **REQUEST_CONTEXT)

    def test_update_raises_validation_error_for_past_time(
        self, service: AppointmentService
    ):
        created = service.create_appointment(_create_payload(), **REQUEST_CONTEXT)
        payload = AppointmentUpdate(
            patient_id="12345",
            patient_name="Test User",
            clinic="Cardiology",
            appointment_time=_past_time(),
        )
        with pytest.raises(AppointmentValidationError):
            service.update_appointment(created.id, payload, **REQUEST_CONTEXT)

    def test_update_preserves_status(self, service: AppointmentService):
        created = service.create_appointment(_create_payload(), **REQUEST_CONTEXT)
        service.cancel_appointment(created.id, **REQUEST_CONTEXT)

        payload = AppointmentUpdate(
            patient_id="12345",
            patient_name="Updated Name",
            clinic="Cardiology",
            appointment_time=_future_time(),
        )
        updated = service.update_appointment(created.id, payload, **REQUEST_CONTEXT)

        # Status must remain CANCELLED — update_appointment never changes
        # status, only cancel_appointment (via set_status) does.
        assert updated.status == "CANCELLED"
        assert updated.patient_name == "Updated Name"


class TestCancelAppointment:
    def test_cancel_raises_not_found_for_missing_id(self, service: AppointmentService):
        with pytest.raises(AppointmentNotFoundError):
            service.cancel_appointment("nonexistent-id", **REQUEST_CONTEXT)

    def test_cancel_sets_status_to_cancelled(self, service: AppointmentService):
        created = service.create_appointment(_create_payload(), **REQUEST_CONTEXT)
        cancelled = service.cancel_appointment(created.id, **REQUEST_CONTEXT)
        assert cancelled.status == "CANCELLED"

    def test_cancel_is_idempotent(self, service: AppointmentService):
        created = service.create_appointment(_create_payload(), **REQUEST_CONTEXT)
        first = service.cancel_appointment(created.id, **REQUEST_CONTEXT)
        second = service.cancel_appointment(created.id, **REQUEST_CONTEXT)
        assert first.status == second.status == "CANCELLED"


class TestDeleteAppointment:
    def test_delete_raises_not_found_for_missing_id(self, service: AppointmentService):
        with pytest.raises(AppointmentNotFoundError):
            service.delete_appointment("nonexistent-id", **REQUEST_CONTEXT)

    def test_delete_removes_appointment(self, service: AppointmentService):
        created = service.create_appointment(_create_payload(), **REQUEST_CONTEXT)
        service.delete_appointment(created.id, **REQUEST_CONTEXT)
        with pytest.raises(AppointmentNotFoundError):
            service.get_appointment(created.id)


class TestListAppointments:
    def test_list_filters_by_patient_id(self, service: AppointmentService):
        service.create_appointment(
            _create_payload(patient_id="11111"), **REQUEST_CONTEXT
        )
        service.create_appointment(
            _create_payload(patient_id="22222"), **REQUEST_CONTEXT
        )

        result = service.list_appointments(
            patient_id="11111", status=None, page=1, size=20
        )

        assert result.total == 1
        assert result.items[0].patient_id == "11111"

    def test_list_filters_by_status(self, service: AppointmentService):
        first = service.create_appointment(_create_payload(), **REQUEST_CONTEXT)
        service.create_appointment(_create_payload(), **REQUEST_CONTEXT)
        service.cancel_appointment(first.id, **REQUEST_CONTEXT)

        result = service.list_appointments(
            patient_id=None, status="CANCELLED", page=1, size=20
        )

        assert result.total == 1
        assert result.items[0].id == first.id
