# =============================================================================
# Appointment domain model
# =============================================================================
# NOTE (Purpose):
# - Internal representation of an appointment record as held by the
#   repository layer. Distinct from API request/response schemas in
#   app/schemas/appointment.py — this separation allows the internal
#   representation to evolve independently of the public API contract
#   (e.g. when PostgreSQL arrives and ORM fields differ from API fields).

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

AppointmentStatus = Literal["BOOKED", "CANCELLED"]


class AppointmentRecord(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    clinic: str
    appointment_time: datetime
    status: AppointmentStatus = "BOOKED"
    created_at: datetime
    updated_at: datetime
