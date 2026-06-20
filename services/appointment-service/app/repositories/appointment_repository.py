# =============================================================================
# In-memory appointment repository
# =============================================================================
# NOTE (Purpose):
# - Provides CRUD data access for AppointmentRecord, isolated from business
#   logic (app/services/appointment_service.py) and API contracts
#   (app/schemas/appointment.py).
# - In-memory only — no persistence across restarts. PostgreSQL planned.
# - Designed so the public interface (list/get/create/update/cancel)
#   would remain stable if swapped for a SQLAlchemy-backed implementation.

# =============================================================================
# In-memory appointment repository
# =============================================================================
# NOTE (Purpose):
# - Provides CRUD data access for AppointmentRecord, isolated from business
#   logic (app/services/appointment_service.py) and API contracts
#   (app/schemas/appointment.py).
# - In-memory only — no persistence across restarts. PostgreSQL planned.
# - Designed so the public interface (list/get/create/update/set_status/
#   delete) would remain stable if swapped for a SQLAlchemy-backed
#   implementation.
# - Instantiated per app instance in main.py's lifespan context manager,
#   not as a module-level singleton — keeps tests isolated by default.

from __future__ import annotations

from app.models.appointment import AppointmentRecord


class InMemoryAppointmentRepository:
    def __init__(self) -> None:
        self._records: dict[str, AppointmentRecord] = {}

    def list(self) -> list[AppointmentRecord]:
        return list(self._records.values())

    def get(self, appointment_id: str) -> AppointmentRecord | None:
        return self._records.get(appointment_id)

    def create(self, record: AppointmentRecord) -> AppointmentRecord:
        self._records[record.id] = record
        return record

    def update(
        self, appointment_id: str, record: AppointmentRecord
    ) -> AppointmentRecord | None:
        if appointment_id not in self._records:
            return None
        self._records[appointment_id] = record
        return record

    def set_status(self, appointment_id: str, status: str) -> AppointmentRecord | None:
        existing = self._records.get(appointment_id)
        if not existing:
            return None
        updated = existing.model_copy(update={"status": status})
        self._records[appointment_id] = updated
        return updated

    def delete(self, appointment_id: str) -> bool:
        if appointment_id not in self._records:
            return False
        del self._records[appointment_id]
        return True

    def seed(self, records: list[AppointmentRecord]) -> None:
        for record in records:
            self._records[record.id] = record

    def clear(self) -> None:
        self._records.clear()
