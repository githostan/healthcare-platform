
"""
Unit tests for patient schemas.

Purpose:
- Validate field-level rules before data reaches service/repository layers
- Check NHS number, DOB, gender, contact method, names, and email validation
"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.patient import PatientBase


BASE = {
    "nhs_number": "9434765919",
    "first_name": "Test",
    "last_name": "Patient",
    "date_of_birth": "1990-01-01",
    "gender": "MALE",
    "registered_practice_code": "L83120",
}


def test_valid_patient_schema():
    PatientBase.model_validate(BASE)


def test_invalid_nhs_number_format():
    with pytest.raises(ValidationError):
        PatientBase.model_validate({**BASE, "nhs_number": "123"})


def test_invalid_nhs_check_digit():
    with pytest.raises(ValidationError):
        PatientBase.model_validate({**BASE, "nhs_number": "1234567890"})


def test_future_date_of_birth_rejected():
    with pytest.raises(ValidationError):
        PatientBase.model_validate({**BASE, "date_of_birth": "2099-01-01"})


def test_today_date_of_birth_rejected():
    with pytest.raises(ValidationError):
        PatientBase.model_validate({**BASE, "date_of_birth": date.today().isoformat()})


def test_invalid_gender_rejected():
    with pytest.raises(ValidationError):
        PatientBase.model_validate({**BASE, "gender": "INVALID"})


def test_invalid_contact_method_rejected():
    with pytest.raises(ValidationError):
        PatientBase.model_validate({**BASE, "preferred_contact_method": "INVALID"})


def test_invalid_email_rejected():
    with pytest.raises(ValidationError):
        PatientBase.model_validate({**BASE, "email": "not-an-email"})


def test_empty_first_name_rejected():
    with pytest.raises(ValidationError):
        PatientBase.model_validate({**BASE, "first_name": ""})