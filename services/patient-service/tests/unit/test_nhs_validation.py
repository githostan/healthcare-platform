"""
Unit tests for NHS number utilities.

Purpose:
- Test NHS check digit logic independently from FastAPI
- Confirm generated NHS numbers are valid and unique enough for test data
"""

from app.schemas.patient import PatientBase
from app.utils.nhs import calculate_nhs_check_digit, generate_valid_nhs_number


def test_valid_nhs_check_digit():
    """
    9434765919 is a known valid NHS number.
    The first 9 digits should calculate check digit 9.
    """
    assert calculate_nhs_check_digit("943476591") == 9


def test_invalid_prefix_returns_none():
    """
    Invalid prefixes should return None rather than raising.
    """
    assert calculate_nhs_check_digit("12345") is None
    assert calculate_nhs_check_digit("abcdefghi") is None


def test_generate_valid_nhs_number_passes_schema_validation():
    """
    Generated NHS numbers should pass the same validation used by API payloads.
    """
    nhs_number = generate_valid_nhs_number()

    PatientBase.model_validate(
        {
            "nhs_number": nhs_number,
            "first_name": "Test",
            "last_name": "Patient",
            "date_of_birth": "1990-01-01",
            "gender": "MALE",
            "registered_practice_code": "L83120",
        }
    )


def test_generate_produces_unique_numbers():
    """
    Generate 100 numbers and confirm no duplicates in this small sample.
    """
    numbers = {generate_valid_nhs_number() for _ in range(100)}

    assert len(numbers) == 100
