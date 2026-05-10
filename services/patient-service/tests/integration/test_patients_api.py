"""
Integration tests for Patient API.

Purpose:
- Test route → middleware → service → repository flow
- Validate status codes, response bodies, filtering, and pagination
"""

from app.utils.nhs import generate_valid_nhs_number


def fresh_payload() -> dict:
    return {
        "nhs_number": generate_valid_nhs_number(),
        "first_name": "Integration",
        "last_name": "Test",
        "date_of_birth": "1990-01-01",
        "gender": "MALE",
        "registered_practice_code": "L83120",
        "status": "ACTIVE",
    }


def test_create_patient_returns_201(client, api_key_headers):
    response = client.post(
        "/api/v1/patients",
        json=fresh_payload(),
        headers=api_key_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ACTIVE"
    assert "id" in data
    assert "created_at" in data


def test_duplicate_nhs_number_returns_409(client, api_key_headers):
    payload = fresh_payload()

    client.post("/api/v1/patients", json=payload, headers=api_key_headers)
    response = client.post("/api/v1/patients", json=payload, headers=api_key_headers)

    assert response.status_code == 409


def test_invalid_nhs_number_returns_422(client, api_key_headers):
    payload = {**fresh_payload(), "nhs_number": "1234567890"}

    response = client.post("/api/v1/patients", json=payload, headers=api_key_headers)

    assert response.status_code == 422


def test_get_patient_by_id(client, api_key_headers):
    created = client.post(
        "/api/v1/patients",
        json=fresh_payload(),
        headers=api_key_headers,
    ).json()

    response = client.get(
        f"/api/v1/patients/{created['id']}",
        headers=api_key_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_nonexistent_patient_returns_404(client, api_key_headers):
    response = client.get(
        "/api/v1/patients/nonexistent-id",
        headers=api_key_headers,
    )

    assert response.status_code == 404


def test_get_by_nhs_number(client, api_key_headers):
    payload = fresh_payload()

    client.post("/api/v1/patients", json=payload, headers=api_key_headers)

    response = client.get(
        f"/api/v1/patients/by-nhs-number/{payload['nhs_number']}",
        headers=api_key_headers,
    )

    assert response.status_code == 200
    assert response.json()["nhs_number"] == payload["nhs_number"]


def test_list_patients_returns_200(client, api_key_headers):
    response = client.get("/api/v1/patients", headers=api_key_headers)

    assert response.status_code == 200


def test_list_pagination(client, api_key_headers):
    for _ in range(5):
        client.post("/api/v1/patients", json=fresh_payload(), headers=api_key_headers)

    response = client.get(
        "/api/v1/patients?page=1&size=2",
        headers=api_key_headers,
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) <= 2
    assert response.json()["page"] == 1
    assert response.json()["size"] == 2


def test_list_filter_by_status(client, api_key_headers):
    client.post("/api/v1/patients", json=fresh_payload(), headers=api_key_headers)

    response = client.get(
        "/api/v1/patients?status=ACTIVE",
        headers=api_key_headers,
    )

    assert response.status_code == 200
    assert all(patient["status"] == "ACTIVE" for patient in response.json()["items"])


def test_update_patient(client, api_key_headers):
    created = client.post(
        "/api/v1/patients",
        json=fresh_payload(),
        headers=api_key_headers,
    ).json()

    update = {**fresh_payload(), "first_name": "Updated"}

    response = client.put(
        f"/api/v1/patients/{created['id']}",
        json=update,
        headers=api_key_headers,
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"


def test_update_status(client, api_key_headers):
    created = client.post(
        "/api/v1/patients",
        json=fresh_payload(),
        headers=api_key_headers,
    ).json()

    response = client.patch(
        f"/api/v1/patients/{created['id']}/status",
        json={"status": "INACTIVE"},
        headers=api_key_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"


def test_soft_delete_returns_204(client, api_key_headers):
    created = client.post(
        "/api/v1/patients",
        json=fresh_payload(),
        headers=api_key_headers,
    ).json()

    response = client.delete(
        f"/api/v1/patients/{created['id']}",
        headers=api_key_headers,
    )

    assert response.status_code == 204


def test_soft_delete_sets_inactive(client, api_key_headers):
    created = client.post(
        "/api/v1/patients",
        json=fresh_payload(),
        headers=api_key_headers,
    ).json()

    client.delete(f"/api/v1/patients/{created['id']}", headers=api_key_headers)

    response = client.get(
        "/api/v1/patients?include_inactive=true",
        headers=api_key_headers,
    )

    ids = [patient["id"] for patient in response.json()["items"]]
    assert created["id"] in ids


def test_eligibility_active_patient(client, api_key_headers):
    created = client.post(
        "/api/v1/patients",
        json=fresh_payload(),
        headers=api_key_headers,
    ).json()

    response = client.get(
        f"/api/v1/patients/{created['id']}/eligibility",
        headers=api_key_headers,
    )

    assert response.status_code == 200
    assert response.json()["eligible_for_booking"] is True


def test_eligibility_nonexistent_patient(client, api_key_headers):
    response = client.get(
        "/api/v1/patients/ghost-id/eligibility",
        headers=api_key_headers,
    )

    assert response.status_code == 200
    assert response.json()["exists"] is False
    assert response.json()["eligible_for_booking"] is False
