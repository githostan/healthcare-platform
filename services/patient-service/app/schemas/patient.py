
# =============================================================================
# Patient domain schemas (validation, structure, and API-facing models)
# =============================================================================
# NOTE (Purpose):
# - Defines the Pydantic models that represent patient data across the API,
#   service, and repository layers. These schemas enforce structural integrity,
#   field-level validation, and domain rules at the boundary of the system.
#
# - Centralises NHS number validation using the shared modulus‑11 algorithm
#   from `app.utils.nhs`, ensuring the generator, validator, and service logic
#   all rely on the same implementation with no duplication or drift.
#
# - Applies strict validation for names, date of birth, gender, contact
#   preferences, and registered practice codes, ensuring that only well-formed
#   patient records enter the system.
#
# - `PatientBase` provides the core reusable fields, while specialised models
#   (create, update, output, list responses) extend this base to support
#   different API operations without repeating validation logic.
#
# - Designed to be stable, testable, and explicit: all validation rules live
#   here, not in the service or repository layers, keeping the domain model
#   consistent across the entire platform.


from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.nhs import calculate_nhs_check_digit

PatientStatus = Literal["ACTIVE", "INACTIVE"]
Gender = Literal["MALE", "FEMALE", "OTHER", "UNKNOWN"]
ContactMethod = Literal["SMS", "EMAIL", "PHONE", "NONE"]


class PatientBase(BaseModel):
    nhs_number: str = Field(pattern=r"^[0-9]{10}$")
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    gender: Gender
    phone: str | None = None
    email: EmailStr | None = None
    preferred_contact_method: ContactMethod = "NONE"
    registered_practice_code: str = Field(min_length=3, max_length=20)

    @field_validator("nhs_number")
    @classmethod
    def validate_nhs_number(cls, value: str) -> str:
        check_digit = calculate_nhs_check_digit(value[:9])
        if check_digit is None or check_digit != int(value[9]):
            raise ValueError("Invalid NHS number check digit")

        return value

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return value

class PatientCreate(PatientBase):
    status: PatientStatus = "ACTIVE"


class PatientUpdate(PatientBase):
    pass


class PatientStatusUpdate(BaseModel):
    status: PatientStatus


class PatientOut(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: PatientStatus
    created_at: datetime
    updated_at: datetime


class PatientListResponse(BaseModel):
    items: list[PatientOut]
    page: int
    size: int
    total: int


class PatientEligibilityResponse(BaseModel):
    patient_id: str
    exists: bool
    status: PatientStatus | None
    eligible_for_booking: bool


class ErrorResponse(BaseModel):
    detail: str
