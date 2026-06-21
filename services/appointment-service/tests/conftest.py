"""
Shared pytest fixtures for appointment-service.

Important:
- Environment variables must be set BEFORE importing app.main.
- This prevents Pydantic Settings from failing during app import.
"""

import os

os.environ.setdefault("APPOINTMENT_SERVICE_API_KEY", "test-appointment-api-key")
os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("ENABLE_LAB_ENDPOINTS", "false")
os.environ.setdefault("DEFAULT_PAGE_SIZE", "20")
os.environ.setdefault("MAX_PAGE_SIZE", "100")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """
    Shared FastAPI test client.
    TestClient triggers the FastAPI lifespan/startup logic, which creates
    app.state.appointment_service.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_appointment_repository(client: TestClient) -> None:
    """
    Clear in-memory appointment data before each test.
    This keeps tests isolated and prevents one test's created appointments
    from leaking into another test.
    """
    service = client.app.state.appointment_service
    service.repository.clear()


@pytest.fixture
def api_key_headers() -> dict[str, str]:
    """
    Valid API key header for protected endpoints.
    """
    return {"X-API-Key": os.environ["APPOINTMENT_SERVICE_API_KEY"]}


@pytest.fixture
def valid_appointment_payload() -> dict:
    """
    Standard valid appointment payload used across API/schema/service tests.
    """
    return {
        "patient_id": "12345",
        "patient_name": "Test User",
        "clinic": "Cardiology",
        "appointment_time": "2030-01-01T10:00:00Z",
    }
