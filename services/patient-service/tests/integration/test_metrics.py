
"""
Integration tests for Prometheus metrics.

Purpose:
- Confirm metrics endpoint is protected
- Confirm metrics payload contains expected counters/histograms
"""


def test_metrics_endpoint_returns_prometheus_format(client, api_key_headers):
    client.get("/healthz")

    response = client.get("/metrics", headers=api_key_headers)

    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text


def test_metrics_requires_valid_api_key(client):
    response = client.get("/metrics")

    assert response.status_code == 401
