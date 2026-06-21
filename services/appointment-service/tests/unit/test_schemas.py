"""
Unit tests for appointment schemas.

Purpose:
- Validate field-level rules before data reaches service/repository layers
- Note: appointment-service's schemas carry minimal field-level validation
  by design — the "appointment_time must be in the future" rule lives in
  AppointmentService, not the schema, so it is NOT tested here. See
  tests/unit/test_appointment_service.py for that coverage.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.appointment import AppointmentRecord
from app.schemas.appointment import AppointmentCreate, AppointmentOut

BASE = {
    "patient_id": "12345",
    "patient_name": "Test User",
    "clinic": "Cardiology",
    "appointment_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
}


def test_valid_appointment_create_schema():
    AppointmentCreate.model_validate(BASE)


def test_empty_patient_id_rejected():
    with pytest.raises(ValidationError):
        AppointmentCreate.model_validate({**BASE, "patient_id": ""})


def test_empty_patient_name_rejected():
    with pytest.raises(ValidationError):
        AppointmentCreate.model_validate({**BASE, "patient_name": ""})


def test_empty_clinic_rejected():
    with pytest.raises(ValidationError):
        AppointmentCreate.model_validate({**BASE, "clinic": ""})


def test_invalid_appointment_time_format_rejected():
    with pytest.raises(ValidationError):
        AppointmentCreate.model_validate({**BASE, "appointment_time": "not-a-date"})


def test_appointment_out_constructs_from_domain_record():
    now = datetime.now(timezone.utc)
    record = AppointmentRecord(
        id="test-id",
        patient_id="12345",
        patient_name="Test User",
        clinic="Cardiology",
        appointment_time=now + timedelta(days=1),
        status="BOOKED",
        created_at=now,
        updated_at=now,
    )

    out = AppointmentOut.model_validate(record)

    assert out.id == "test-id"
    assert out.status == "BOOKED"
