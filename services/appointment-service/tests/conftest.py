import os

import pytest
from fastapi.testclient import TestClient

from app.main import app, _DB


@pytest.fixture(autouse=True)
def set_test_api_key(monkeypatch) -> None:
    """Set a safe test-only API key for all tests."""
    monkeypatch.setenv("APPOINTMENT_API_KEY", "test-appointment-api-key")


@pytest.fixture(autouse=True)
def clear_db() -> None:
    """Reset the in-memory database before each test."""
    _DB.clear()


@pytest.fixture
def client() -> TestClient:
    """Shared FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def api_key_headers() -> dict[str, str]:
    """API key header for protected endpoints."""
    return {"X-API-Key": os.environ["APPOINTMENT_API_KEY"]}
