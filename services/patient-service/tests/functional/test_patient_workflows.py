
"""
Functional tests for patient workflows.

Purpose:
- Validate real business flows across multiple API calls
- Test behaviour from the perspective of a service consumer
"""

from app.utils.nhs import generate_valid_nhs_number


def test_full_patient_lifecycle(client, api_key_headers):
    """
    Create → retrieve → check eligibility → deactivate → verify ineligible.
    """
    payload = {
        "nhs_number": generate_valid_nhs_number(),
        "first_name": "Lifecycle",
        "last_name": "Test",
        "date_of_birth": "1985-06-15",
        "gender": "FEMALE",
        "registered_practice_code": "L83120",
        "status": "ACTIVE",
    }

    created = client.post(
        "/api/v1/patients",
        json=payload,
        headers=api_key_headers,
    ).json()

    patient_id = created["id"]
    assert created["status"] == "ACTIVE"

    retrieved = client.get(
        f"/api/v1/patients/{patient_id}",
        headers=api_key_headers,
    ).json()

    assert retrieved["nhs_number"] == payload["nhs_number"]

    eligibility = client.get(
        f"/api/v1/patients/{patient_id}/eligibility",
        headers=api_key_headers,
    ).json()

    assert eligibility["eligible_for_booking"] is True

    client.patch(
        f"/api/v1/patients/{patient_id}/status",
        json={"status": "INACTIVE"},
        headers=api_key_headers,
    )

    eligibility_after_deactivation = client.get(
        f"/api/v1/patients/{patient_id}/eligibility",
        headers=api_key_headers,
    ).json()

    assert eligibility_after_deactivation["eligible_for_booking"] is False


def test_nhs_number_uniqueness_enforced_across_operations(client, api_key_headers):
    """
    The same NHS number cannot be registered twice.
    """
    payload = {
        "nhs_number": generate_valid_nhs_number(),
        "first_name": "First",
        "last_name": "Patient",
        "date_of_birth": "1990-01-01",
        "gender": "MALE",
        "registered_practice_code": "L83120",
        "status": "ACTIVE",
    }

    first_response = client.post(
        "/api/v1/patients",
        json=payload,
        headers=api_key_headers,
    )

    second_response = client.post(
        "/api/v1/patients",
        json=payload,
        headers=api_key_headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_inactive_patient_excluded_from_default_list(client, api_key_headers):
    """
    Inactive patients should not appear in the default list response.
    """
    payload = {
        "nhs_number": generate_valid_nhs_number(),
        "first_name": "Hidden",
        "last_name": "Patient",
        "date_of_birth": "1990-01-01",
        "gender": "MALE",
        "registered_practice_code": "L83120",
        "status": "INACTIVE",
    }

    created = client.post(
        "/api/v1/patients",
        json=payload,
        headers=api_key_headers,
    ).json()

    response = client.get("/api/v1/patients", headers=api_key_headers)
    ids = [patient["id"] for patient in response.json()["items"]]

    assert created["id"] not in ids