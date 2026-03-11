from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture(autouse=True)
def clear_db() -> None:
    """
    Reset the in-memory database before each test.
    """
    _DB.clear()


@pytest.fixture
def client() -> TestClient:
    """
    Shared FastAPI test client.
    """
    return TestClient(app)


@pytest.fixture
def api_key_headers() -> dict[str, str]:
    """
    Default API key header for protected endpoints.
    """
    return {"X-API-Key": "dev-secret-key"}
