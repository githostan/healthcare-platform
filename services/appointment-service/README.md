

# appointment-service

A FastAPI microservice responsible for managing appointment lifecycle operations
within the Healthcare Platform.

---

## Overview

`appointment-service` handles the full appointment lifecycle — creation, retrieval,
update, cancellation, and deletion. It is deployed to a single-node k3s cluster,
instrumented for observability, and secured via API key authentication.

This service was also the primary learning ground for Kubernetes failure drills,
rolling update behaviour, probe configuration, and resource management.

---

## Current Status

| Area              | Status                                         |
|-------------------|------------------------------------------------|
| API functionality | ✅ Complete                                    |
| Auth (API key)    | ⚠️ Being migrated to environment-based config  |
| Observability     | ✅ Structured JSON logs + Prometheus metrics   |
| CI/CD             | ✅ GitHub Actions → GHCR                       |
| Deployment        | ✅ k3s (single-node)                           |
| Failure drills    | ✅ Implemented and documented                  |
| Code structure    | ⚠️ Monolithic — scheduled for modularisation  |
| Demo UI           | ⚠️ Temporary — will be removed                |

---

## Responsibilities

### Owns

- Appointment lifecycle (`BOOKED → CANCELLED`)
- Appointment validation (future-time enforcement)
- API interface for all appointment operations

### Does Not Own

- Patient data — delegated to `patient-service`
- Clinic data — delegated to `clinic-service` (future)

---

## API Reference

### Health Probes

```bash
GET /healthz      # Liveness probe
GET /readyz       # Readiness probe
GET /startupz     # Startup probe
```

### Appointments

```bash
GET    /api/v1/appointments              # List all appointments
POST   /api/v1/appointments              # Create appointment
GET    /api/v1/appointments/{id}         # Get by ID
PUT    /api/v1/appointments/{id}         # Full update
PATCH  /api/v1/appointments/{id}/cancel  # Cancel appointment
DELETE /api/v1/appointments/{id}         # Delete appointment
```

### Observability

```bash
GET /metrics      # Prometheus metrics endpoint
```

### Demo UI (Temporary)

```bash
GET  /ui
GET  /ui/appointments
GET  /ui/appointments/new
POST /ui/appointments
```

> ⚠️ This UI is tightly coupled to the backend and will be removed in favour
> of the dedicated `healthcare-ui` frontend service.

### Lab Endpoints (Dev Only)

```bash
GET /lab/slow?seconds=<n>   # Simulate latency
GET /lab/fail               # Trigger deliberate failure
```

Controlled by environment variable:

```dotenv
ENABLE_LAB_ENDPOINTS=true
```

Used for load testing with `hey`, probe failure drills, and observability
validation.

---

## Authentication

All `/api/v1/*` endpoints require an API key header:

```
X-API-Key: <your-api-key>
```

> ⚠️ The API key was previously hardcoded and committed to source control.
> This is actively being migrated to environment-based configuration via
> Kubernetes secrets.

---

## Running Locally

```bash
uvicorn app.main:app --reload
```

### Create an Appointment

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/appointments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{
    "patient_id": "123",
    "patient_name": "John Doe",
    "clinic": "GP",
    "appointment_time": "2026-05-01T10:00:00"
  }';echo
```

---

## Data Model

### Appointment

| Field              | Type                    | Notes                         |
|--------------------|-------------------------|-------------------------------|
| `id`               | `string` (UUID)         | Auto-generated                |
| `patient_id`       | `string`                | Reference to `patient-service`|
| `patient_name`     | `string`                | Denormalised — to be removed  |
| `clinic`           | `string`                |                               |
| `appointment_time` | `datetime`              | Must be in the future         |
| `status`           | `BOOKED` \| `CANCELLED` |                               |

> **Note:** `patient_name` is currently duplicated from patient data. This will
> be removed once inter-service communication with `patient-service` is in place.

**Storage:** In-memory list (`_DB`). No persistence. Data is lost on restart.

---

## Observability

### Logging

- Structured JSON output
- Request ID propagation per request
- Error logging with full stack traces

### Metrics

| Metric                          | Type      | Description                            |
|---------------------------------|-----------|----------------------------------------|
| `http_requests_total`           | Counter   | Total requests by method, path, status |
| `http_request_duration_seconds` | Histogram | Request latency by path                |

---

## Failure Drills

This service was used to study and document Kubernetes failure behaviour. All
scenarios were drilled, observed, and documented in `docs/runbooks/`.

| Scenario                   | Observed Behaviour                                  |
|----------------------------|-----------------------------------------------------|
| Bad secret reference       | `CreateContainerConfigError`, old pod retained      |
| Bad image tag              | `ImagePullBackOff`, old pod retained                |
| Memory limit too low       | `OOMKilled` → `CrashLoopBackOff`                    |
| Insufficient node memory   | `Pending` / `FailedScheduling`                      |
| Liveness probe failure     | Container killed, `CrashLoopBackOff`, service down  |
| Readiness probe failure    | Pod excluded from endpoints, old pod retained       |
| Broken service selector    | `Endpoints: <none>`, service unreachable            |
| Wrong `targetPort`         | Endpoints populated but traffic fails               |

### Lab Endpoints

```bash
# Simulate slow response (used with hey for load testing)
curl "http://127.0.0.1:8000/lab/slow?seconds=5"

# Trigger deliberate 500 failure
curl "http://127.0.0.1:8000/lab/fail"
```

---

## Deployment

- Built via GitHub Actions on push to `main` (app changes only)
- Docker image published to GHCR
- Deployed to k3s via `kubectl apply`
- Kubernetes objects: `Namespace`, `Secret`, `Deployment`, `Service`

---

## Known Limitations

| Limitation                         | Notes                                          |
|------------------------------------|------------------------------------------------|
| In-memory datastore                | No persistence across restarts                 |
| `patient_name` denormalised        | Patient data duplicated inside appointment     |
| No inter-service validation        | Booking does not check patient eligibility yet |
| Monolithic structure               | All logic lives in `app/main.py`               |
| Demo UI tightly coupled to backend | To be replaced by `healthcare-ui`              |

---

## Planned Evolution

### 🔥 Immediate

- [ ] Move API key to environment variables — remove all hardcoded secrets
- [ ] Modularise into the standard service layout:

```
app/
├── routes/
├── schemas/
├── models/
├── services/
├── repositories/
├── middleware/
├── config/
└── utils/
```

### 🔗 Integration

- [ ] Integrate with `patient-service` eligibility check before accepting a booking:

```bash
GET /api/v1/patients/{patient_id}/eligibility
# Reject if: "eligible_for_booking": false
```

### 🎯 Platform Direction

- [ ] Replace demo UI with `healthcare-ui` frontend service
- [ ] Add PostgreSQL persistence
- [ ] Introduce typed service-to-service HTTP clients with retry and timeout logic
- [ ] Move deployment to GitOps via ArgoCD

---

## Summary

`appointment-service` is a fully working, Kubernetes-deployed microservice
instrumented for observability and battle-tested through structured failure
drills. It currently operates as a working prototype — the foundation is solid,
and the next phase evolves it from a working service into a production-grade
architecture consistent with `patient-service`.