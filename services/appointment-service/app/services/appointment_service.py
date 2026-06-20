# =============================================================================
# Appointment domain service (business logic, validation, audit logging)
# =============================================================================
# NOTE (Purpose):
# - Implements all appointment-related business operations: creation,
#   updates, cancellation, deletion, and listing with filters.
# - Acts as the orchestration layer between API routes and the repository,
#   enforcing domain rules (e.g. appointment_time must be in the future).
# - Framework-independent: raises domain exceptions (AppointmentNotFoundError,
#   AppointmentValidationError), never fastapi.HTTPException. The API layer
#   (app/api/v1/appointments.py) is responsible for translating these into
#   HTTP responses. This keeps the service layer testable and reusable
#   outside of a FastAPI request context.
# - NOTE: patient-service's PatientService currently raises HTTPException
#   directly — appointment-service intentionally diverges here as the
#   more correct pattern. patient-service should be backported
#   to this pattern in a future refactor.
# - Emits structured audit logs for all mutating actions, including request
#   and correlation IDs and an API-key fingerprint for traceability.
# - Converts repository records into Pydantic response schemas for
#   consistent API output formatting.
# - set_status is reserved exclusively for the cancel operation — general
#   field changes always go through update(), never set_status(), to keep
#   the repository's narrow-update guarantee meaningful at the call site.
# - NOTE: AppointmentListResponse is a pagination envelope, not strictly an
#   HTTP contract — returning it from the service is acceptable, but it is
#   currently defined in app/schemas/ alongside true API contracts. Consider
#   relocating to app/models/ or app/schemas/common.py if this distinction
#   matters later.

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.models.appointment import AppointmentRecord
from app.repositories.appointment_repository import InMemoryAppointmentRepository
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentOut,
    AppointmentStatus,
    AppointmentUpdate,
)
from app.utils.security import fingerprint_api_key


class AppointmentNotFoundError(Exception):
    """Raised when an appointment lookup by ID finds no record."""


class AppointmentValidationError(Exception):
    """Raised when a domain validation rule is violated (e.g. past appointment_time)."""


class AppointmentService:
    def __init__(
        self,
        repository: InMemoryAppointmentRepository,
        logger: logging.Logger,
    ) -> None:
        self.repository = repository
        self.logger = logger

    def _audit(
        self,
        *,
        action: str,
        resource_id: str,
        request_id: str,
        correlation_id: str,
        api_key: str,
        outcome: str,
    ) -> None:
        self.logger.info(
            "audit",
            extra={
                "action": action,
                "resource_type": "appointment",
                "resource_id": resource_id,
                "request_id": request_id,
                "correlation_id": correlation_id,
                "api_key_fingerprint": fingerprint_api_key(api_key),
                "outcome": outcome,
            },
        )

    def _to_schema(self, record: AppointmentRecord) -> AppointmentOut:
        return AppointmentOut.model_validate(record)

    def _require_future(self, dt: datetime) -> None:
        # If client sends a naive datetime, assume UTC to avoid surprises.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt <= datetime.now(timezone.utc):
            raise AppointmentValidationError("appointment_time must be in the future")

    def _get_record(self, appointment_id: str) -> AppointmentRecord:
        """
        Fetch a record by ID or raise AppointmentNotFoundError.
        Centralises the fetch-or-fail pattern used by every read/write
        operation that requires an existing appointment.
        """
        record = self.repository.get(appointment_id)
        if not record:
            raise AppointmentNotFoundError("Appointment not found")
        return record

    # ── Read operations ───────────────────────────────────────────

    def list_appointments(
        self,
        *,
        patient_id: str | None,
        status: AppointmentStatus | None,
        page: int,
        size: int,
    ) -> AppointmentListResponse:
        items = self.repository.list()

        if patient_id:
            items = [a for a in items if a.patient_id == patient_id]

        if status:
            items = [a for a in items if a.status == status]

        total = len(items)
        start = (page - 1) * size
        paged = items[start : start + size]

        return AppointmentListResponse(
            items=[self._to_schema(a) for a in paged],
            page=page,
            size=size,
            total=total,
        )

    def get_appointment(self, appointment_id: str) -> AppointmentOut:
        record = self._get_record(appointment_id)
        return self._to_schema(record)

    # ── Write operations ──────────────────────────────────────────

    def create_appointment(
        self,
        payload: AppointmentCreate,
        *,
        request_id: str,
        correlation_id: str,
        api_key: str,
    ) -> AppointmentOut:
        try:
            self._require_future(payload.appointment_time)

            now = datetime.now(timezone.utc)
            record = AppointmentRecord(
                id=str(uuid4()),
                patient_id=payload.patient_id,
                patient_name=payload.patient_name,
                clinic=payload.clinic,
                appointment_time=payload.appointment_time,
                status="BOOKED",
                created_at=now,
                updated_at=now,
            )
            self.repository.create(record)

            self._audit(
                action="create",
                resource_id=record.id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome="success",
            )
            return self._to_schema(record)

        except (AppointmentNotFoundError, AppointmentValidationError) as exc:
            self._audit(
                action="create",
                resource_id="unknown",
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome=f"failed:{type(exc).__name__}",
            )
            raise

    def update_appointment(
        self,
        appointment_id: str,
        payload: AppointmentUpdate,
        *,
        request_id: str,
        correlation_id: str,
        api_key: str,
    ) -> AppointmentOut:
        try:
            self._require_future(payload.appointment_time)
            existing = self._get_record(appointment_id)

            updated = AppointmentRecord(
                id=existing.id,
                patient_id=payload.patient_id,
                patient_name=payload.patient_name,
                clinic=payload.clinic,
                appointment_time=payload.appointment_time,
                # NOTE: status is intentionally preserved, not taken from
                # payload — status transitions go through cancel_appointment
                # (set_status) only, never through a full update.
                status=existing.status,
                created_at=existing.created_at,
                updated_at=datetime.now(timezone.utc),
            )
            self.repository.update(appointment_id, updated)

            self._audit(
                action="update",
                resource_id=appointment_id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome="success",
            )
            return self._to_schema(updated)

        except (AppointmentNotFoundError, AppointmentValidationError) as exc:
            self._audit(
                action="update",
                resource_id=appointment_id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome=f"failed:{type(exc).__name__}",
            )
            raise

    def cancel_appointment(
        self,
        appointment_id: str,
        *,
        request_id: str,
        correlation_id: str,
        api_key: str,
    ) -> AppointmentOut:
        try:
            existing = self._get_record(appointment_id)

            # Idempotent — cancelling an already-cancelled appointment
            # returns the existing record without another audit entry.
            if existing.status == "CANCELLED":
                return self._to_schema(existing)

            updated = self.repository.set_status(appointment_id, "CANCELLED")
            if updated is None:
                raise AppointmentNotFoundError("Appointment not found")

            self._audit(
                action="cancel",
                resource_id=appointment_id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome="success",
            )
            return self._to_schema(updated)

        except (AppointmentNotFoundError, AppointmentValidationError) as exc:
            self._audit(
                action="cancel",
                resource_id=appointment_id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome=f"failed:{type(exc).__name__}",
            )
            raise

    def delete_appointment(
        self,
        appointment_id: str,
        *,
        request_id: str,
        correlation_id: str,
        api_key: str,
    ) -> None:
        try:
            self._get_record(appointment_id)
            self.repository.delete(appointment_id)

            self._audit(
                action="delete",
                resource_id=appointment_id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome="success",
            )

        except (AppointmentNotFoundError, AppointmentValidationError) as exc:
            self._audit(
                action="delete",
                resource_id=appointment_id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome=f"failed:{type(exc).__name__}",
            )
            raise
