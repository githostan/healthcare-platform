# smoke testing


def test_health_smoke(client):
    r = client.get("/healthz")
    assert r.status_code == 200
