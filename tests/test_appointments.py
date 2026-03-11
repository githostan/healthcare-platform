# these validate the actual API features: creating, retrieving, cancelling, deleting appointments

"""Tests for appointment CRUD operations."""

API_KEY = {"X-API-Key": "dev-secret-key"}


def test_create_appointment(client):
    """Test creating a new appointment with valid data."""
    payload = {
        "patient_id": "12345",
        "patient_name": "Test User",
        "clinic": "Cardiology",
        "appointment_time": "2030-01-01T10:00:00Z",
    }

    response = client.post("/api/v1/appointments", json=payload, headers=API_KEY)

    assert response.status_code == 201

    data = response.json()

    assert data["patient_id"] == "12345"
    assert data["patient_name"] == "Test User"
    assert data["clinic"] == "Cardiology"
    assert data["status"] == "BOOKED"
