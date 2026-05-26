"""
Smoke tests.

Purpose:
- Confirm the application starts
- Confirm public operational endpoints respond
"""


def test_healthz(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz(client):
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_startupz(client):
    response = client.get("/startupz")

    assert response.status_code == 200
    assert response.json() == {"status": "started"}


def test_info(client):
    response = client.get("/info")

    assert response.status_code == 200
    assert response.json()["service"] == "patient-service"


def test_docs_accessible(client):
    response = client.get("/docs")

    assert response.status_code == 200
