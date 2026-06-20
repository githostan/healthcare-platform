# =============================================================================
# Appointment API schemas (request/response contracts)
# =============================================================================
# NOTE (Purpose):
# - Defines the Pydantic models used directly in FastAPI route signatures.
# - AppointmentCreate/AppointmentUpdate validate incoming request bodies.
# - AppointmentOut is the public response shape, distinct from the internal
#   AppointmentRecord domain model in app/models/appointment.py.
# - AppointmentListResponse wraps paginated list results consistently with
#   patient-service's PatientListResponse pattern.

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AppointmentStatus = Literal["BOOKED", "CANCELLED"]


class AppointmentCreate(BaseModel):
    patient_id: str = Field(min_length=1)
    patient_name: str = Field(min_length=1)
    clinic: str = Field(min_length=1)
    appointment_time: datetime


class AppointmentUpdate(BaseModel):
    patient_id: str = Field(min_length=1)
    patient_name: str = Field(min_length=1)
    clinic: str = Field(min_length=1)
    appointment_time: datetime


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    patient_name: str
    clinic: str
    appointment_time: datetime
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime


class AppointmentListResponse(BaseModel):
    items: list[AppointmentOut]
    page: int
    size: int
    total: int
