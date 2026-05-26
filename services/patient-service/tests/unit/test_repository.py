"""
Unit tests for InMemoryPatientRepository.

Purpose:
- Test repository behaviour independently from HTTP and service layers
- Validate create, get, list, update, and status operations
"""

import pytest

from app.repositories.patient_repository import InMemoryPatientRepository
from app.schemas.patient import PatientCreate, PatientUpdate
from app.utils.nhs import generate_valid_nhs_number


@pytest.fixture
def repo() -> InMemoryPatientRepository:
    return InMemoryPatientRepository()


@pytest.fixture
def payload() -> PatientCreate:
    return PatientCreate(
        nhs_number=generate_valid_nhs_number(),
        first_name="Repo",
        last_name="Test",
        date_of_birth="1990-01-01",
        gender="MALE",
        registered_practice_code="L83120",
        status="ACTIVE",
    )


def test_create_and_retrieve(repo, payload):
    record = repo.create(payload)
    retrieved = repo.get(record.id)

    assert retrieved is not None
    assert retrieved.id == record.id


def test_get_nonexistent_returns_none(repo):
    assert repo.get("nonexistent") is None


def test_get_by_nhs_number(repo, payload):
    record = repo.create(payload)
    retrieved = repo.get_by_nhs_number(payload.nhs_number)

    assert retrieved is not None
    assert retrieved.id == record.id


def test_get_by_nhs_number_not_found_returns_none(repo):
    assert repo.get_by_nhs_number("0000000000") is None


def test_list_returns_all_records(repo, payload):
    repo.create(payload)

    second = PatientCreate(
        nhs_number=generate_valid_nhs_number(),
        first_name="Second",
        last_name="Patient",
        date_of_birth="1985-03-10",
        gender="FEMALE",
        registered_practice_code="L83120",
        status="ACTIVE",
    )
    repo.create(second)

    assert len(repo.list()) == 2


def test_set_status_updates_record(repo, payload):
    record = repo.create(payload)
    updated = repo.set_status(record.id, "INACTIVE")

    assert updated is not None
    assert updated.status == "INACTIVE"


def test_set_status_nonexistent_returns_none(repo):
    assert repo.set_status("nonexistent", "INACTIVE") is None


def test_update_modifies_fields(repo, payload):
    record = repo.create(payload)

    update = PatientUpdate(
        nhs_number=payload.nhs_number,
        first_name="Updated",
        last_name="Name",
        date_of_birth="1990-01-01",
        gender="MALE",
        registered_practice_code="L83120",
    )

    updated = repo.update(record.id, update)

    assert updated is not None
    assert updated.first_name == "Updated"


def test_update_nonexistent_returns_none(repo, payload):
    update = PatientUpdate(
        nhs_number=payload.nhs_number,
        first_name="X",
        last_name="Y",
        date_of_birth="1990-01-01",
        gender="MALE",
        registered_practice_code="L83120",
    )

    assert repo.update("nonexistent", update) is None
