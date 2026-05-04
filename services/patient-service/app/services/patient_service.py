
# =============================================================================
# Patient domain service (business logic, validation, audit logging)
# =============================================================================
# NOTE (Purpose):
# - Implements all patient-related business operations: creation, updates,
#   status changes, soft deletion, NHS-number lookup, pagination, and
#   eligibility evaluation.
# - Acts as the orchestration layer between API routes and the repository,
#   enforcing domain rules and raising HTTP exceptions for invalid operations.
# - Emits structured audit logs for all mutating actions, including request and
#   correlation IDs and an API-key fingerprint for traceability.
# - Converts repository records into Pydantic response schemas for consistent
#   API output formatting.
# - Designed for clean separation of concerns: routes → service → repository.

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from app.models.patient import PatientRecord
from app.repositories.patient_repository import InMemoryPatientRepository
from app.schemas.patient import (
    PatientCreate,
    PatientEligibilityResponse,
    PatientListResponse,
    PatientOut,
    PatientStatus,
    PatientStatusUpdate,
    PatientUpdate,
)
from app.utils.security import fingerprint_api_key


class PatientService:
    def __init__(self, repository: InMemoryPatientRepository, logger: logging.Logger) -> None:
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
                "resource_type": "patient",
                "resource_id": resource_id,
                "request_id": request_id,
                "correlation_id": correlation_id,
                "api_key_fingerprint": fingerprint_api_key(api_key),
                "outcome": outcome,
            },
        )

    def _to_schema(self, record: PatientRecord) -> PatientOut:
        return PatientOut.model_validate(record)

    def list_patients(
        self,
        *,
        status: PatientStatus | None,
        registered_practice_code: str | None,
        include_inactive: bool,
        page: int,
        size: int,
    ) -> PatientListResponse:
        # NOTE:
        # Filtering is currently done in-memory because this service uses an
        # InMemoryPatientRepository. When moving to Postgres, push these filters
        # down into query predicates at the repository/database layer.
        items = self.repository.list()

        if not include_inactive:
            items = [p for p in items if p.status == "ACTIVE"]

        if status:
            items = [p for p in items if p.status == status]

        if registered_practice_code:
            items = [
                p for p in items if p.registered_practice_code == registered_practice_code
            ]

        total = len(items)
        start = (page - 1) * size
        end = start + size
        paged = items[start:end]

        return PatientListResponse(
            items=[self._to_schema(p) for p in paged],
            page=page,
            size=size,
            total=total,
        )

    def get_patient(self, patient_id: str) -> PatientOut:
        record = self.repository.get(patient_id)
        if not record:
            raise HTTPException(status_code=404, detail="Patient not found")
        return self._to_schema(record)

    def get_by_nhs_number(self, nhs_number: str) -> PatientOut:
        record = self.repository.get_by_nhs_number(nhs_number)
        if not record:
            raise HTTPException(status_code=404, detail="Patient not found")
        return self._to_schema(record)

    def create_patient(
        self,
        payload: PatientCreate,
        *,
        request_id: str,
        correlation_id: str,
        api_key: str,
    ) -> PatientOut:
        try:
            if self.repository.get_by_nhs_number(payload.nhs_number):
                raise HTTPException(
                    status_code=409,
                    detail="Patient NHS number already exists",
                )

            record = self.repository.create(payload)

            self._audit(
                action="create",
                resource_id=record.id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome="success",
            )

            return self._to_schema(record)

        except HTTPException as exc:
            self._audit(
                action="create",
                resource_id="unknown",
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome=f"failed:{exc.status_code}",
            )
            raise

    def update_patient(
        self,
        patient_id: str,
        payload: PatientUpdate,
        *,
        request_id: str,
        correlation_id: str,
        api_key: str,
    ) -> PatientOut:
        try:
            # NOTE:
            # This uniqueness check is sufficient for the in-memory repository.
            # When moving to Postgres, enforce NHS number uniqueness with a
            # database-level unique constraint as well.
            existing_by_nhs = self.repository.get_by_nhs_number(payload.nhs_number)
            if existing_by_nhs and existing_by_nhs.id != patient_id:
                raise HTTPException(
                    status_code=409,
                    detail="Patient NHS number already exists",
                )

            record = self.repository.update(patient_id, payload)
            if not record:
                raise HTTPException(status_code=404, detail="Patient not found")

            self._audit(
                action="update",
                resource_id=record.id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome="success",
            )

            return self._to_schema(record)

        except HTTPException as exc:
            self._audit(
                action="update",
                resource_id=patient_id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome=f"failed:{exc.status_code}",
            )
            raise

    def update_status(
        self,
        patient_id: str,
        payload: PatientStatusUpdate,
        *,
        request_id: str,
        correlation_id: str,
        api_key: str,
    ) -> PatientOut:
        try:
            record = self.repository.set_status(patient_id, payload.status)
            if not record:
                raise HTTPException(status_code=404, detail="Patient not found")

            self._audit(
                action="status_update",
                resource_id=record.id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome="success",
            )

            return self._to_schema(record)

        except HTTPException as exc:
            self._audit(
                action="status_update",
                resource_id=patient_id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome=f"failed:{exc.status_code}",
            )
            raise

    def soft_delete(
        self,
        patient_id: str,
        *,
        request_id: str,
        correlation_id: str,
        api_key: str,
    ) -> None:
        try:
            record = self.repository.set_status(patient_id, "INACTIVE")
            if not record:
                raise HTTPException(status_code=404, detail="Patient not found")

            self._audit(
                action="soft_delete",
                resource_id=record.id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome="success",
            )

        except HTTPException as exc:
            self._audit(
                action="soft_delete",
                resource_id=patient_id,
                request_id=request_id,
                correlation_id=correlation_id,
                api_key=api_key,
                outcome=f"failed:{exc.status_code}",
            )
            raise

    def get_eligibility(self, patient_id: str) -> PatientEligibilityResponse:
        record = self.repository.get(patient_id)
        if not record:
            return PatientEligibilityResponse(
                patient_id=patient_id,
                exists=False,
                status=None,
                eligible_for_booking=False,
            )

        return PatientEligibilityResponse(
            patient_id=patient_id,
            exists=True,
            status=record.status,
            eligible_for_booking=(record.status == "ACTIVE"),
        )

    def seed_data(self) -> None:
        now = datetime.now(timezone.utc)

        seeded = [
            PatientRecord(
                id=str(uuid4()),
                nhs_number="9434765919",  # valid
                first_name="Ada",
                last_name="Nwachukwu",
                date_of_birth=date(1990, 1, 15),
                gender="FEMALE",
                phone="07123456789",
                email="ada@example.com",
                preferred_contact_method="SMS",
                registered_practice_code="L83120",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            ),
            PatientRecord(
                id=str(uuid4()),
                nhs_number="4857773456",  # valid
                first_name="John",
                last_name="Smith",
                date_of_birth=date(1983, 7, 7),
                gender="MALE",
                phone="07000000000",
                email="john@example.com",
                preferred_contact_method="EMAIL",
                registered_practice_code="A12345",
                status="INACTIVE",
                created_at=now,
                updated_at=now,
            ),
        ]

        self.repository.seed(seeded)