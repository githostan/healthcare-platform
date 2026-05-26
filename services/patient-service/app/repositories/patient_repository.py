# =============================================================================
# In‑memory patient repository (temporary persistence layer)
# =============================================================================
# NOTE (Purpose):
# - Provides a simple, in‑memory persistence mechanism for patient records.
# - Used during early development, local testing, and service bring‑up before
#   introducing a real database-backed repository (e.g., PostgreSQL).
# - Implements the full repository interface expected by PatientService:
#   listing, retrieval, NHS-number lookup, creation, updates, status changes,
#   and seeding of initial records.
# - Stores PatientRecord instances in a dictionary keyed by patient ID for
#   O(1) access and predictable behaviour across service operations.
# - Designed for clean separation of concerns: routes → service → repository.

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import uuid4

from app.models.patient import PatientRecord
from app.schemas.patient import PatientCreate, PatientStatus, PatientUpdate


class InMemoryPatientRepository:
    def __init__(self) -> None:
        self._items: dict[str, PatientRecord] = {}

    def list(self) -> list[PatientRecord]:
        return list(self._items.values())

    def get(self, patient_id: str) -> PatientRecord | None:
        return self._items.get(patient_id)

    def get_by_nhs_number(self, nhs_number: str) -> PatientRecord | None:
        return next(
            (p for p in self._items.values() if p.nhs_number == nhs_number), None
        )

    def create(self, payload: PatientCreate) -> PatientRecord:
        now = datetime.now(timezone.utc)
        record = PatientRecord(
            id=str(uuid4()),
            nhs_number=payload.nhs_number,
            first_name=payload.first_name,
            last_name=payload.last_name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            phone=payload.phone,
            email=payload.email,
            preferred_contact_method=payload.preferred_contact_method,
            registered_practice_code=payload.registered_practice_code,
            status=payload.status,
            created_at=now,
            updated_at=now,
        )
        self._items[record.id] = record
        return record

    def update(self, patient_id: str, payload: PatientUpdate) -> PatientRecord | None:
        record = self._items.get(patient_id)
        if not record:
            return None
        record.nhs_number = payload.nhs_number
        record.first_name = payload.first_name
        record.last_name = payload.last_name
        record.date_of_birth = payload.date_of_birth
        record.gender = payload.gender
        record.phone = payload.phone
        record.email = payload.email
        record.preferred_contact_method = payload.preferred_contact_method
        record.registered_practice_code = payload.registered_practice_code
        record.updated_at = datetime.now(timezone.utc)
        return record

    def set_status(
        self, patient_id: str, status: PatientStatus
    ) -> PatientRecord | None:
        record = self._items.get(patient_id)
        if not record:
            return None
        record.status = status
        record.updated_at = datetime.now(timezone.utc)
        return record

    def seed(self, records: Iterable[PatientRecord]) -> None:
        for record in records:
            self._items[record.id] = record
