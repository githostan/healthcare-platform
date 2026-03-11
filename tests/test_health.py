
def test_healthz(client):
    """Test that the health check endpoint returns healthy status."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz(client):
    """Test that the readiness probe indicates service is ready."""
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_info(client):
    """Test that service metadata endpoint returns correct information."""
    response = client.get("/info")
    assert response.status_code == 200
    assert response.json()["service"] == "appointment-api"
    assert "version" in response.json()