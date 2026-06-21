"""
Unit tests for InMemoryAppointmentRepository.

Purpose:
- Test repository behaviour independently from HTTP and service layers
- Validate create, get, list, update, set_status, delete, and clear
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.appointment import AppointmentRecord
from app.repositories.appointment_repository import InMemoryAppointmentRepository


@pytest.fixture
def repo() -> InMemoryAppointmentRepository:
    return InMemoryAppointmentRepository()


def _record(**overrides) -> AppointmentRecord:
    now = datetime.now(timezone.utc)
    defaults = {
        "id": str(uuid4()),
        "patient_id": "12345",
        "patient_name": "Repo Test",
        "clinic": "Cardiology",
        "appointment_time": now + timedelta(days=1),
        "status": "BOOKED",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return AppointmentRecord(**defaults)


def test_create_and_retrieve(repo: InMemoryAppointmentRepository):
    record = _record()
    repo.create(record)
    retrieved = repo.get(record.id)

    assert retrieved is not None
    assert retrieved.id == record.id


def test_get_nonexistent_returns_none(repo: InMemoryAppointmentRepository):
    assert repo.get("nonexistent") is None


def test_list_returns_all_records(repo: InMemoryAppointmentRepository):
    repo.create(_record())
    repo.create(_record(patient_id="67890"))

    assert len(repo.list()) == 2


def test_update_modifies_fields(repo: InMemoryAppointmentRepository):
    record = _record()
    repo.create(record)

    updated_record = record.model_copy(update={"patient_name": "Updated"})
    result = repo.update(record.id, updated_record)

    assert result is not None
    assert result.patient_name == "Updated"


def test_update_nonexistent_returns_none(repo: InMemoryAppointmentRepository):
    record = _record()
    assert repo.update("nonexistent", record) is None


def test_set_status_updates_status(repo: InMemoryAppointmentRepository):
    record = _record()
    repo.create(record)

    updated = repo.set_status(record.id, "CANCELLED")

    assert updated is not None
    assert updated.status == "CANCELLED"


def test_set_status_nonexistent_returns_none(repo: InMemoryAppointmentRepository):
    assert repo.set_status("nonexistent", "CANCELLED") is None


def test_set_status_preserves_other_fields(repo: InMemoryAppointmentRepository):
    record = _record(patient_name="Original Name")
    repo.create(record)

    updated = repo.set_status(record.id, "CANCELLED")

    assert updated is not None
    assert updated.patient_name == "Original Name"
    assert updated.id == record.id


def test_delete_removes_record(repo: InMemoryAppointmentRepository):
    record = _record()
    repo.create(record)

    result = repo.delete(record.id)

    assert result is True
    assert repo.get(record.id) is None


def test_delete_nonexistent_returns_false(repo: InMemoryAppointmentRepository):
    assert repo.delete("nonexistent") is False


def test_seed_adds_multiple_records(repo: InMemoryAppointmentRepository):
    records = [_record(), _record(patient_id="67890")]
    repo.seed(records)

    assert len(repo.list()) == 2


def test_clear_removes_all_records(repo: InMemoryAppointmentRepository):
    repo.create(_record())
    repo.create(_record(patient_id="67890"))

    repo.clear()

    assert repo.list() == []
