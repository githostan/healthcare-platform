
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
# - Adds OpenTelemetry business spans, repository sub-spans, business events,
#   and safe non-PII attributes for Tempo/Grafana trace analysis.

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

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

tracer = trace.get_tracer(__name__)


class PatientService:
    def __init__(
        self,
        repository: InMemoryPatientRepository,
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

    # ── Read operations ───────────────────────────────────────────

    def list_patients(
        self,
        *,
        status: PatientStatus | None,
        registered_practice_code: str | None,
        include_inactive: bool,
        page: int,
        size: int,
    ) -> PatientListResponse:
        with tracer.start_as_current_span(
            "patient.list",
            kind=SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("query.include_inactive", include_inactive)
            span.set_attribute("query.page", page)
            span.set_attribute("query.size", size)

            if status:
                span.set_attribute("query.status", str(status))

            if registered_practice_code:
                span.set_attribute(
                    "query.registered_practice_code",
                    registered_practice_code,
                )

            # NOTE: Filtering is in-memory now. When PostgreSQL arrives,
            # push these predicates down to the query layer.
            with tracer.start_as_current_span(
                "repository.patient.list",
                kind=SpanKind.INTERNAL,
            ) as repository_span:
                items = self.repository.list()
                repository_span.set_attribute("repository.result_count", len(items))

            span.set_attribute("result.records_before_filter", len(items))

            if not include_inactive:
                items = [p for p in items if p.status == "ACTIVE"]

            if status:
                items = [p for p in items if p.status == status]

            if registered_practice_code:
                items = [
                    p
                    for p in items
                    if p.registered_practice_code == registered_practice_code
                ]

            total = len(items)
            start = (page - 1) * size
            paged = items[start : start + size]

            span.set_attribute("result.total", total)
            span.set_attribute("result.page_count", len(paged))
            span.add_event(
                "patients_listed",
                {
                    "result.total": total,
                    "result.page_count": len(paged),
                },
            )

            return PatientListResponse(
                items=[self._to_schema(p) for p in paged],
                page=page,
                size=size,
                total=total,
            )

    def get_patient(self, patient_id: str) -> PatientOut:
        with tracer.start_as_current_span(
            "patient.get",
            kind=SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("patient.id", patient_id)

            with tracer.start_as_current_span(
                "repository.patient.get",
                kind=SpanKind.INTERNAL,
            ):
                record = self.repository.get(patient_id)

            if not record:
                span.set_status(Status(StatusCode.ERROR, "Patient not found"))
                span.set_attribute("error.type", "not_found")
                span.add_event("patient_not_found")
                raise HTTPException(status_code=404, detail="Patient not found")

            span.set_attribute("patient.status", record.status)
            span.add_event("patient_retrieved")
            return self._to_schema(record)

    def get_by_nhs_number(self, nhs_number: str) -> PatientOut:
        with tracer.start_as_current_span(
            "patient.get_by_nhs_number",
            kind=SpanKind.INTERNAL,
        ) as span:
            # Do not set nhs_number as span attribute — PII.
            with tracer.start_as_current_span(
                "repository.patient.get_by_nhs_number",
                kind=SpanKind.INTERNAL,
            ):
                record = self.repository.get_by_nhs_number(nhs_number)

            if not record:
                span.set_status(Status(StatusCode.ERROR, "Patient not found"))
                span.set_attribute("error.type", "not_found")
                span.add_event("patient_not_found")
                raise HTTPException(status_code=404, detail="Patient not found")

            span.set_attribute("patient.id", str(record.id))
            span.set_attribute("patient.status", record.status)
            span.add_event("patient_retrieved_by_nhs_number")
            return self._to_schema(record)

    def get_eligibility(self, patient_id: str) -> PatientEligibilityResponse:
        with tracer.start_as_current_span(
            "patient.eligibility.check",
            kind=SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("patient.id", patient_id)

            with tracer.start_as_current_span(
                "repository.patient.get",
                kind=SpanKind.INTERNAL,
            ):
                record = self.repository.get(patient_id)

            if not record:
                span.set_attribute("eligibility.result", "not_found")
                span.set_attribute("eligibility.eligible", False)
                span.add_event("eligibility_checked_not_found")
                return PatientEligibilityResponse(
                    patient_id=patient_id,
                    exists=False,
                    status=None,
                    eligible_for_booking=False,
                )

            eligible = record.status == "ACTIVE"
            span.set_attribute("patient.status", record.status)
            span.set_attribute(
                "eligibility.result",
                "eligible" if eligible else "ineligible",
            )
            span.set_attribute("eligibility.eligible", eligible)
            span.add_event(
                "eligibility_checked",
                {
                    "eligibility.eligible": eligible,
                    "patient.status": record.status,
                },
            )

            return PatientEligibilityResponse(
                patient_id=patient_id,
                exists=True,
                status=record.status,
                eligible_for_booking=eligible,
            )

    # ── Write operations ──────────────────────────────────────────

    def create_patient(
        self,
        payload: PatientCreate,
        *,
        request_id: str,
        correlation_id: str,
        api_key: str,
    ) -> PatientOut:
        with tracer.start_as_current_span(
            "patient.create",
            kind=SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("request.id", request_id)
            span.set_attribute("correlation.id", correlation_id)
            # Do not set nhs_number — PII.

            try:
                with tracer.start_as_current_span(
                    "repository.patient.get_by_nhs_number",
                    kind=SpanKind.INTERNAL,
                ):
                    existing = self.repository.get_by_nhs_number(payload.nhs_number)

                if existing:
                    span.set_status(
                        Status(StatusCode.ERROR, "NHS number already exists")
                    )
                    span.set_attribute("error.type", "duplicate_nhs_number")
                    span.add_event("patient_create_rejected_duplicate_nhs_number")
                    raise HTTPException(
                        status_code=409,
                        detail="Patient NHS number already exists",
                    )

                with tracer.start_as_current_span(
                    "repository.patient.create",
                    kind=SpanKind.INTERNAL,
                ):
                    record = self.repository.create(payload)

                span.set_attribute("patient.id", str(record.id))
                span.set_attribute("patient.status", record.status)
                span.add_event(
                    "patient_created",
                    {
                        "patient.id": str(record.id),
                        "patient.status": record.status,
                    },
                )

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
        with tracer.start_as_current_span(
            "patient.update",
            kind=SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("patient.id", patient_id)
            span.set_attribute("request.id", request_id)
            span.set_attribute("correlation.id", correlation_id)

            try:
                # NOTE: When PostgreSQL arrives, enforce uniqueness via
                # database constraint in addition to this check.
                with tracer.start_as_current_span(
                    "repository.patient.get_by_nhs_number",
                    kind=SpanKind.INTERNAL,
                ):
                    existing_by_nhs = self.repository.get_by_nhs_number(
                        payload.nhs_number
                    )

                if existing_by_nhs and existing_by_nhs.id != patient_id:
                    span.set_status(
                        Status(StatusCode.ERROR, "NHS number conflict")
                    )
                    span.set_attribute("error.type", "nhs_number_conflict")
                    span.add_event("patient_update_rejected_nhs_number_conflict")
                    raise HTTPException(
                        status_code=409,
                        detail="Patient NHS number already exists",
                    )

                with tracer.start_as_current_span(
                    "repository.patient.update",
                    kind=SpanKind.INTERNAL,
                ):
                    record = self.repository.update(patient_id, payload)

                if not record:
                    span.set_status(Status(StatusCode.ERROR, "Patient not found"))
                    span.set_attribute("error.type", "not_found")
                    span.add_event("patient_update_failed_not_found")
                    raise HTTPException(status_code=404, detail="Patient not found")

                span.set_attribute("patient.status", record.status)
                span.add_event(
                    "patient_updated",
                    {
                        "patient.id": str(record.id),
                        "patient.status": record.status,
                    },
                )

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
        with tracer.start_as_current_span(
            "patient.status.update",
            kind=SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("patient.id", patient_id)
            span.set_attribute("request.id", request_id)
            span.set_attribute("correlation.id", correlation_id)
            span.set_attribute("status.new", str(payload.status))

            try:
                with tracer.start_as_current_span(
                    "repository.patient.get",
                    kind=SpanKind.INTERNAL,
                ):
                    existing = self.repository.get(patient_id)

                if not existing:
                    span.set_status(Status(StatusCode.ERROR, "Patient not found"))
                    span.set_attribute("error.type", "not_found")
                    span.add_event("patient_status_update_failed_not_found")
                    raise HTTPException(status_code=404, detail="Patient not found")

                previous_status = existing.status
                span.set_attribute("status.previous", previous_status)

                with tracer.start_as_current_span(
                    "repository.patient.set_status",
                    kind=SpanKind.INTERNAL,
                ):
                    record = self.repository.set_status(patient_id, payload.status)

                if not record:
                    span.set_status(Status(StatusCode.ERROR, "Patient not found"))
                    span.set_attribute("error.type", "not_found")
                    span.add_event("patient_status_update_failed_not_found")
                    raise HTTPException(status_code=404, detail="Patient not found")

                span.set_attribute("patient.status", record.status)
                span.add_event(
                    "patient_status_changed",
                    {
                        "patient.id": str(record.id),
                        "status.previous": previous_status,
                        "status.new": str(payload.status),
                    },
                )

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
        with tracer.start_as_current_span(
            "patient.soft_delete",
            kind=SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("patient.id", patient_id)
            span.set_attribute("request.id", request_id)
            span.set_attribute("correlation.id", correlation_id)

            try:
                with tracer.start_as_current_span(
                    "repository.patient.get",
                    kind=SpanKind.INTERNAL,
                ):
                    existing = self.repository.get(patient_id)

                if not existing:
                    span.set_status(Status(StatusCode.ERROR, "Patient not found"))
                    span.set_attribute("error.type", "not_found")
                    span.add_event("patient_soft_delete_failed_not_found")
                    raise HTTPException(status_code=404, detail="Patient not found")

                previous_status = existing.status

                with tracer.start_as_current_span(
                    "repository.patient.set_status",
                    kind=SpanKind.INTERNAL,
                ):
                    record = self.repository.set_status(patient_id, "INACTIVE")

                if not record:
                    span.set_status(Status(StatusCode.ERROR, "Patient not found"))
                    span.set_attribute("error.type", "not_found")
                    span.add_event("patient_soft_delete_failed_not_found")
                    raise HTTPException(status_code=404, detail="Patient not found")

                span.set_attribute("status.previous", previous_status)
                span.set_attribute("status.new", "INACTIVE")
                span.add_event(
                    "patient_soft_deleted",
                    {
                        "patient.id": str(record.id),
                        "status.previous": previous_status,
                        "status.new": "INACTIVE",
                    },
                )

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

    # ── Seed data ─────────────────────────────────────────────────

    def seed_data(self) -> None:
        now = datetime.now(timezone.utc)
        seeded = [
            PatientRecord(
                id=str(uuid4()),
                nhs_number="9434765919",
                first_name="Zoe",
                last_name="Brown",
                date_of_birth=date(1990, 1, 15),
                gender="FEMALE",
                phone="07123456789",
                email="zoe@example.com",
                preferred_contact_method="SMS",
                registered_practice_code="L83120",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            ),
            PatientRecord(
                id=str(uuid4()),
                nhs_number="4857773456",
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

        