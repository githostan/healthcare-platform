
# =============================================================================
# Patient domain model (internal persistence representation)
# =============================================================================
# NOTE (Purpose):
# - Defines the canonical patient entity used internally by the service and
#   repository layers. This model represents how patient data is stored and
#   manipulated within the system.
# - Implemented as a `slots=True` dataclass for lightweight, memory‑efficient,
#   and attribute‑safe record handling without Pydantic validation overhead.
# - Kept separate from API-facing schemas (PatientCreate, PatientUpdate,
#   PatientOut) to maintain a clean boundary between internal storage models
#   and external request/response contracts.
# - Used exclusively by the repository and service layers to ensure a clear,
#   maintainable separation of concerns across the application.

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

PatientStatus = Literal["ACTIVE", "INACTIVE"]
Gender = Literal["MALE", "FEMALE", "OTHER", "UNKNOWN"]
ContactMethod = Literal["SMS", "EMAIL", "PHONE", "NONE"]


@dataclass(slots=True)
class PatientRecord:
    id: str
    nhs_number: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    phone: str | None
    email: str | None
    preferred_contact_method: ContactMethod
    registered_practice_code: str
    status: PatientStatus
    created_at: datetime
    updated_at: datetime