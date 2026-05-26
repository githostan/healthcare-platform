"""
Integration tests for authentication behaviour.

Purpose:
- Confirm protected endpoints enforce API key authentication
- Confirm public health endpoints remain unauthenticated
"""


def test_no_api_key_returns_401(client):
    response = client.get("/api/v1/patients")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


def test_wrong_api_key_returns_403(client):
    response = client.get(
        "/api/v1/patients",
        headers={"X-API-Key": "wrong"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid API key"


def test_valid_api_key_returns_200(client, api_key_headers):
    response = client.get("/api/v1/patients", headers=api_key_headers)

    assert response.status_code == 200


def test_metrics_requires_auth(client):
    response = client.get("/metrics")

    assert response.status_code == 401


def test_health_endpoints_require_no_auth(client):
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    assert client.get("/startupz").status_code == 200
    assert client.get("/info").status_code == 200
