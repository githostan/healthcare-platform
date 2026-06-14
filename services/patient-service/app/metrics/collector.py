
# =============================================================================
# Prometheus metric definitions for patient-service
# =============================================================================
# All metrics defined here as module-level singletons.
# Import from here wherever metrics need to be incremented or observed.
# Centralising definitions prevents duplicate registration errors on reload.
#
# Current metrics:
#   REQUEST_COUNT    — total HTTP requests by method, path, status
#   REQUEST_LATENCY  — HTTP request duration histogram by path
#
# Add new metrics here as the service grows:
#   - Business metrics (patients_created_total, eligibility_checks_total)
#   - Auth metrics (auth_failures_total)
#   - Rate limit metrics (rate_limit_hits_total)
# =============================================================================

from prometheus_client import Counter, Histogram

# ── HTTP request metrics (RED — Rate, Errors, Duration) ───────────────────────

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests received by patient-service",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)