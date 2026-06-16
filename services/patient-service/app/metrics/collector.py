# =============================================================================
# Prometheus metric definitions for patient-service
# =============================================================================
# All metrics defined here as module-level singletons.
# Import from here wherever metrics need to be incremented or observed.
# Centralising definitions prevents duplicate registration errors on reload.
#
# Metric categories:
#   HTTP metrics     — Rate, Errors, Duration (RED methodology)
#   Patient metrics  — Clinical workflow events for SRE alerting
#   Eligibility      — Critical path for appointment booking
#   Auth metrics     — Authentication failure tracking
#   Rate limiting    — Throttling visibility
#   Service info     — Build and runtime metadata label set
#
# Business metrics are the most operationally valuable.
# An alert on patients_created_total stopping is more actionable
# than a generic HTTP 500 rate alert.
# =============================================================================

import os

from prometheus_client import Counter, Gauge, Histogram, Info

# ── HTTP request metrics (RED — Rate, Errors, Duration) ──────────────────────

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

# ── Patient business metrics ──────────────────────────────────────────────────

patients_created_total = Counter(
    "patients_created_total",
    "Total patients successfully registered",
)

patients_creation_failed_total = Counter(
    "patients_creation_failed_total",
    "Total patient registration failures by reason",
    ["reason"],
)

patients_updated_total = Counter(
    "patients_updated_total",
    "Total patient records successfully updated",
)

patients_status_updated_total = Counter(
    "patients_status_updated_total",
    "Total patient status changes",
    ["new_status"],
)

patients_soft_deleted_total = Counter(
    "patients_soft_deleted_total",
    "Total patients soft-deleted",
)

patients_retrieved_total = Counter(
    "patients_retrieved_total",
    "Total successful patient record retrievals",
    ["method"],
)

patients_lookup_failed_total = Counter(
    "patients_lookup_failed_total",
    "Total failed patient lookups by method and reason",
    ["method", "reason"],
)

active_patients_gauge = Gauge(
    "active_patients_total",
    "Current number of ACTIVE patients in the system",
)

# ── Eligibility metrics ───────────────────────────────────────────────────────
# Eligibility checks are the critical path for appointment booking.
# appointment-service calls GET /patients/{id}/eligibility before every booking.

eligibility_checks_total = Counter(
    "eligibility_checks_total",
    "Total booking eligibility checks performed",
    ["result"],
    # result values:
    #   eligible     — patient exists and is ACTIVE
    #   ineligible   — patient exists but is INACTIVE
    #   not_found    — no patient with this ID
)

# ── Authentication metrics ────────────────────────────────────────────────────

auth_failures_total = Counter(
    "auth_failures_total",
    "Total authentication failures by reason",
    ["reason"],
    # reason values:
    #   missing_key  — X-API-Key header absent (401)
    #   invalid_key  — X-API-Key header present but wrong (403)
)

# ── Rate limiting metrics ─────────────────────────────────────────────────────

rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total requests rejected by rate limiter",
)

# ── Service metadata ──────────────────────────────────────────────────────────
# Static label set on all metrics in Grafana.
# Allows filtering dashboards by version or environment.

service_info = Info(
    "patient_service",
    "patient-service build and runtime metadata",
)

service_info.info(
    {
        "version": os.getenv("SERVICE_VERSION", "0.1.0"),
        "environment": os.getenv("ENVIRONMENT", "dev"),
        "namespace": os.getenv("K8S_NAMESPACE", "healthcare-dev"),
    }
)
