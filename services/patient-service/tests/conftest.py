"""
Shared pytest fixtures for patient-service.

Important:
- Environment variables must be set BEFORE importing app.main.
- This prevents Pydantic Settings from failing during app import.
"""

import os

os.environ.setdefault("PATIENT_SERVICE_API_KEY", "test-patient-api-key")
os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("ENABLE_SEED_DATA", "false")
os.environ.setdefault("DEFAULT_PAGE_SIZE", "20")
os.environ.setdefault("MAX_PAGE_SIZE", "100")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_patient_repository(client: TestClient) -> None:
    service = client.app.state.patient_service
    service.repository._items.clear()


@pytest.fixture
def api_key_headers() -> dict[str, str]:
    return {"X-API-Key": os.environ["PATIENT_SERVICE_API_KEY"]}


@pytest.fixture
def valid_patient_payload() -> dict:
    return {
        "nhs_number": "9434765919",
        "first_name": "Test",
        "last_name": "Patient",
        "date_of_birth": "1990-01-01",
        "gender": "MALE",
        "phone": "07123456789",
        "email": "test.patient@example.com",
        "preferred_contact_method": "SMS",
        "registered_practice_code": "L83120",
        "status": "ACTIVE",
    }


# import os

# os.environ.setdefault("PATIENT_SERVICE_API_KEY", "test-patient-api-key")
# os.environ.setdefault("ENVIRONMENT", "dev")
# os.environ.setdefault("LOG_LEVEL", "INFO")
# os.environ.setdefault("ENABLE_SEED_DATA", "false")
# os.environ.setdefault("DEFAULT_PAGE_SIZE", "20")
# os.environ.setdefault("MAX_PAGE_SIZE", "100")
# os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")

# import pytest
# from fastapi.testclient import TestClient

# from app.main import app


# @pytest.fixture
# def client() -> TestClient:
#     """
#     Shared FastAPI test client.

#     TestClient triggers the FastAPI lifespan/startup logic, which creates
#     app.state.patient_service.
#     """
#     with TestClient(app) as test_client:
#         yield test_client


# @pytest.fixture(autouse=True)
# def reset_patient_repository(client: TestClient) -> None:
#     """
#     Clear in-memory patient data before each test.

#     This keeps tests isolated and prevents one test's created patients from
#     leaking into another test.
#     """
#     service = client.app.state.patient_service
#     service.repository._items.clear()


# @pytest.fixture
# def api_key_headers() -> dict[str, str]:
#     """
#     Valid API key header for protected endpoints.
#     """
#     return {"X-API-Key": os.environ["PATIENT_SERVICE_API_KEY"]}


# @pytest.fixture
# def valid_patient_payload() -> dict:
#     """
#     Standard valid patient payload used across API/schema/service tests.
#     """
#     return {
#         "nhs_number": "9434765919",
#         "first_name": "Test",
#         "last_name": "Patient",
#         "date_of_birth": "1990-01-01",
#         "gender": "MALE",
#         "phone": "07123456789",
#         "email": "test.patient@example.com",
#         "preferred_contact_method": "SMS",
#         "registered_practice_code": "L83120",
#         "status": "ACTIVE",
#     }
