# =============================================================================
# Prometheus metric definitions for appointment-service
# =============================================================================
# NOTE (Purpose):
# - All metrics defined here as module-level singletons. Import from here
#   wherever metrics need to be incremented or observed. Centralising
#   definitions prevents duplicate registration errors on reload.
# - Mirrors patient-service's metrics/collector.py structure: HTTP RED
#   metrics plus business metrics for the domain's mutating operations.
# - Rate limiting metric scaffold added to align with patient-service's
#   sliding-window pattern. Actual rate-limiting middleware is wired later
#   in Step 9 — defining the metric now does not change current behaviour.

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── HTTP request metrics (RED — Rate, Errors, Duration) ──────────────────────

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests received by appointment-service",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ── Appointment business metrics ──────────────────────────────────────────────

appointments_created_total = Counter(
    "appointments_created_total",
    "Total appointments successfully created",
)

appointments_creation_failed_total = Counter(
    "appointments_creation_failed_total",
    "Total appointment creation failures by reason",
    ["reason"],
    # reason values: validation_error (past appointment_time)
)

appointments_updated_total = Counter(
    "appointments_updated_total",
    "Total appointment records successfully updated (PUT)",
)

appointments_cancelled_total = Counter(
    "appointments_cancelled_total",
    "Total appointments cancelled",
)

appointments_deleted_total = Counter(
    "appointments_deleted_total",
    "Total appointments hard-deleted",
)

appointments_retrieved_total = Counter(
    "appointments_retrieved_total",
    "Total successful appointment retrievals",
    ["method"],
    # method values: by_id | list
)

active_appointments_gauge = Gauge(
    "active_appointments_total",
    "Current number of BOOKED (non-cancelled) appointments",
)

# ── Authentication metrics ────────────────────────────────────────────────────

auth_failures_total = Counter(
    "auth_failures_total",
    "Total authentication failures by reason",
    ["reason"],
    # reason values: missing_key | invalid_key
)

# ── Rate limiting metrics ─────────────────────────────────────────────────────

rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total requests rejected by rate limiter (429)",
)
