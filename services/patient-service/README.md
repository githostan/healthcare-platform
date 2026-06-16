
# patient-service

A FastAPI microservice responsible for managing patient identity and profile data
within the BioMeshCore healthcare platform.

---

## Overview

`patient-service` provides a modular, production-representative architecture with
strong validation, structured JSON logging with OTel trace correlation, Prometheus
metrics, API-key authentication, and OpenTelemetry distributed tracing.

Designed for extensibility — storage, messaging, and observability backends are
swappable via environment variables with no code changes.

---

## Current Status

| Area                    | Status                                                  |
|-------------------------|---------------------------------------------------------|
| API functionality       | ✅ Complete                                             |
| Auth (API key)          | ✅ Timing-safe, typed exceptions                        |
| NHS validation          | ✅ Modulus-11 check digit algorithm                     |
| Structured logging      | ✅ JSON + OTel trace/span ID correlation                |
| Prometheus metrics      | ✅ HTTP RED metrics + business metrics                  |
| OpenTelemetry tracing   | ✅ Business spans, repository sub-spans, span events    |
| Rate limiting           | ✅ Per API key, sliding window, in-memory               |
| Audit logging           | ✅ All mutating operations                              |
| CI/CD                   | ✅ GitHub Actions — lint, test, Snyk, build, push       |
| Dockerisation           | ✅ Non-root image, python:3.12-slim                     |
| Deployment              | ✅ k3s homelab (healthcare-dev namespace, NodePort 30801)|
| Persistent storage      | 🔜 PostgreSQL (planned)                                 |

---

## Responsibilities

### Owns

- Patient lifecycle — creation, retrieval, update, soft delete
- NHS number validation (Modulus-11 check digit)
- Patient eligibility checks for downstream services
- Source of truth for patient identity across the platform

### Does Not Own

- Appointment data — `appointment-service`
- Clinic data — `clinic-service` (planned)
- Notifications — `notification-service` (planned)

---

## Architecture

api/v1 → services → repositories → models


| Layer        | Location                    | Responsibility                                         |
|--------------|-----------------------------|--------------------------------------------------------|
| API routes   | `app/api/v1/`               | Endpoints, auth deps, request/response contracts       |
| Auth         | `app/auth/`                 | API key validation, FastAPI dependencies               |
| Services     | `app/services/`             | Business logic, OTel spans, metrics, audit logging     |
| Repositories | `app/repositories/`         | Data access — in-memory now, PostgreSQL planned        |
| Schemas      | `app/schemas/`              | Pydantic request/response models                       |
| Models       | `app/models/`               | Internal domain models                                 |
| Middleware   | `app/middleware/`           | Pure ASGI — request IDs, rate limiting, metrics, logs  |
| Core         | `app/core/`                 | Config, structured logging, OTel bootstrap             |
| Metrics      | `app/metrics/`              | Prometheus metric definitions                          |
| Utils        | `app/utils/`                | NHS validation, crypto helpers                         |

---

## API Reference

### Platform Endpoints (no auth required)

| Endpoint    | Description                           |
|-------------|---------------------------------------|
| `/healthz`  | Liveness probe                        |
| `/readyz`   | Readiness probe                       |
| `/startupz` | Startup completion probe              |
| `/info`     | Service metadata, OTel state, k8s ctx |
| `/metrics`  | Prometheus scrape (API-key required)  |

### Patients — `/api/v1/patients`

| Method   | Endpoint                          | Description                         |
|----------|-----------------------------------|-------------------------------------|
| `GET`    | `/`                               | List patients (filterable, paged)   |
| `POST`   | `/`                               | Register a patient                  |
| `GET`    | `/{patient_id}`                   | Get patient by UUID                 |
| `GET`    | `/by-nhs-number/{nhs_number}`     | Lookup by NHS number                |
| `PUT`    | `/{patient_id}`                   | Full patient update                 |
| `PATCH`  | `/{patient_id}/status`            | Update status (`ACTIVE`/`INACTIVE`) |
| `DELETE` | `/{patient_id}`                   | Soft delete (sets to `INACTIVE`)    |
| `GET`    | `/{patient_id}/eligibility`       | Booking eligibility check           |

### Query Parameters — `GET /api/v1/patients`

| Parameter                  | Type     | Default | Description                      |
|----------------------------|----------|---------|----------------------------------|
| `status`                   | `string` | —       | Filter by `ACTIVE` or `INACTIVE` |
| `registered_practice_code` | `string` | —       | Filter by GP practice ODS code   |
| `include_inactive`         | `bool`   | `false` | Include INACTIVE patients        |
| `page`                     | `int`    | `1`     | Page number (≥ 1)                |
| `size`                     | `int`    | `20`    | Page size (1–100)                |

---

## Authentication

All `/api/v1/*` endpoints require an API key header:


X-API-Key: <your-key>

Configured via environment variable:

```dotenv
PATIENT_SERVICE_API_KEY=your-key-here
```

| Response | Cause           |
|----------|-----------------|
| `401`    | Missing API key |
| `403`    | Invalid API key |

Generate a key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Configuration

| Variable                    | Default        | Description                                   |
|-----------------------------|----------------|-----------------------------------------------|
| `PATIENT_SERVICE_API_KEY`   | **required**   | API key for endpoint authentication            |
| `ENVIRONMENT`               | `dev`          | `dev` \| `staging` \| `prod`                  |
| `LOG_LEVEL`                 | `INFO`         | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR`     |
| `ENABLE_SEED_DATA`          | `true`         | Load seed patients on startup                  |
| `DEFAULT_PAGE_SIZE`         | `20`           | Default pagination page size                   |
| `MAX_PAGE_SIZE`             | `100`          | Maximum pagination page size                   |
| `RATE_LIMIT_PER_MINUTE`     | `60`           | Max requests per API key per minute            |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | unset        | OTel Collector URL (unset = console exporter)  |
| `OTEL_EXPORTER_PROTOCOL`    | `grpc`         | `grpc` or `http`                               |
| `OTEL_SAMPLING_RATIO`       | `1.0`          | Trace sampling ratio (0.0–1.0)                 |
| `K8S_NAMESPACE`             | `healthcare-dev` | Injected by k8s downward API                 |
| `K8S_POD_NAME`              | `unknown`      | Injected by k8s downward API                   |
| `K8S_NODE_NAME`             | `unknown`      | Injected by k8s downward API                   |

Copy `.env.example` to `.env` and fill in values locally. Never commit `.env`.

---

## Running Locally

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set PATIENT_SERVICE_API_KEY

# 4. Start the service
uvicorn app.main:app --reload
```

Service: `http://127.0.0.1:8000`
Swagger UI: `http://127.0.0.1:8000/docs`

---

## Running Tests

```bash
PATIENT_SERVICE_API_KEY=test-key pytest tests -q
```

Test categories:

```bash
pytest tests/unit        # pure logic, no HTTP
pytest tests/integration # full HTTP stack, in-memory repo
pytest tests/functional  # end-to-end business workflows
pytest tests/smoke       # fast sanity checks
```

---

## Example Requests

### Create Patient

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/patients \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-key>" \
  -d '{
    "nhs_number": "9434765919",
    "first_name": "Zoe",
    "last_name": "Brown",
    "date_of_birth": "1990-01-15",
    "gender": "FEMALE",
    "registered_practice_code": "L83120"
  }';echo
```

### Check Eligibility

```bash
curl -H "X-API-Key: <your-key>" \
  http://127.0.0.1:8000/api/v1/patients/<patient_id>/eligibility
```

### Service Info

```bash
curl http://127.0.0.1:8000/info | python3 -m json.tool
```

---

## Data Model

| Field                      | Type                                             | Notes                        |
|----------------------------|--------------------------------------------------|------------------------------|
| `id`                       | `string` (UUID)                                  | Auto-generated               |
| `nhs_number`               | `string` (10 digits)                             | Modulus-11 validated, unique |
| `first_name`               | `string`                                         | 1–100 characters             |
| `last_name`                | `string`                                         | 1–100 characters             |
| `date_of_birth`            | `date`                                           | Must be in the past          |
| `gender`                   | `MALE`\|`FEMALE`\|`OTHER`\|`PREFER_NOT_TO_SAY`  |                              |
| `phone`                    | `string` \| `null`                               | Optional                     |
| `email`                    | `email` \| `null`                                | Optional                     |
| `preferred_contact_method` | `SMS`\|`EMAIL`\|`PHONE`\|`NONE`                  | Default: `NONE`              |
| `registered_practice_code` | `string`                                         | GP practice ODS code         |
| `status`                   | `ACTIVE` \| `INACTIVE`                           | Default: `ACTIVE`            |
| `created_at`               | `datetime`                                       | UTC                          |
| `updated_at`               | `datetime`                                       | UTC                          |

Storage: in-memory repository. Data is lost on pod restart. PostgreSQL planned.

---

## Observability

### OpenTelemetry Tracing

Traces are emitted on every request with full business span hierarchy:

GET /api/v1/patients                    ← HTTP SERVER span (FastAPI auto-instrumentation)
└── patient.list                      ← business span
└── repository.patient.list     ← data access sub-span

Span events on significant business moments:
`patient_created`, `eligibility_checked`, `patient_status_changed`,
`patient_soft_deleted`, `patient_not_found`

PII rule: NHS numbers never appear in span attributes or events.

**Pre-observability mode** (default): `ConsoleSpanExporter` — traces print to stdout.
**With OTel Collector**: set `OTEL_EXPORTER_OTLP_ENDPOINT` — traces route to Tempo.

### Structured Logging

Every log line is JSON with OTel `trace_id` and `span_id` for Loki → Tempo correlation:

```json
{
  "ts": "2026-06-15T21:02:40.835+00:00",
  "level": "INFO",
  "logger": "patient_service",
  "message": "request_complete",
  "trace_id": "ce938baf17cd2c969dfc1864f7150f27",
  "span_id": "5ab9c2e1dce6acd6",
  "trace_sampled": true
}
```

### Prometheus Metrics

| Metric                          | Type      | Labels                        |
|---------------------------------|-----------|-------------------------------|
| `http_requests_total`           | Counter   | `method`, `path`, `status`    |
| `http_request_duration_seconds` | Histogram | `path`                        |
| `patients_created_total`        | Counter   | —                             |
| `patients_creation_failed_total`| Counter   | `reason`                      |
| `patients_updated_total`        | Counter   | —                             |
| `patients_status_updated_total` | Counter   | `new_status`                  |
| `patients_soft_deleted_total`   | Counter   | —                             |
| `patients_retrieved_total`      | Counter   | `method`                      |
| `active_patients_total`         | Gauge     | —                             |
| `eligibility_checks_total`      | Counter   | `result`                      |
| `auth_failures_total`           | Counter   | `reason`                      |
| `rate_limit_hits_total`         | Counter   | —                             |

Accessible at `/metrics` (API-key required).

### Rate Limiting

- Sliding window — 60 requests/minute per API key (configurable)
- Exempt: `/healthz`, `/readyz`, `/startupz`, `/info`, `/metrics`
- Returns `429 Too Many Requests` when exceeded

---

## NHS Number Validation

Validated using the Modulus-11 check digit algorithm:

- Exactly 10 ASCII digits
- Check digit verified against weighted sum
- Uniqueness enforced at create and update
- Never logged, traced, or stored in span attributes (PII)

Generate valid test numbers:

```bash
PYTHONPATH=. python3 -c "
from app.utils.nhs import generate_valid_nhs_number
for _ in range(5):
    print(generate_valid_nhs_number())
"
```

---

## Seed Data

Loaded on startup when `ENABLE_SEED_DATA=true`:

| NHS Number   | Name       | Status     |
|--------------|------------|------------|
| `9434765919` | Zoe Brown  | `ACTIVE`   |
| `4857773456` | John Smith | `INACTIVE` |

---

## Kubernetes

Deployed to `healthcare-dev` namespace on k3s homelab.

```bash
# Check pod status
kubectl get pods -n healthcare-dev -l app=patient-service

# View logs
kubectl logs -n healthcare-dev -l app=patient-service --tail=50

# Service info
curl http://<node-ip>:30801/info | python3 -m json.tool

# Health probes
curl http://<node-ip>:30801/healthz
curl http://<node-ip>:30801/readyz
```

k8s env vars are injected via downward API:
`K8S_NAMESPACE`, `K8S_POD_NAME`, `K8S_NODE_NAME` — visible in `/info` and span attributes.

---

## Known Limitations

| Limitation              | Notes                                               |
|-------------------------|-----------------------------------------------------|
| In-memory storage       | No persistence across pod restarts                  |
| Rate limiting           | Per-process only — not distributed across replicas  |
| No inter-service auth   | JWT / mTLS planned for service-to-service calls     |
| OTel Collector          | Not yet deployed — console exporter active          |

---

## Planned Evolution

### Data

- [ ] PostgreSQL via SQLAlchemy + asyncpg
- [ ] Alembic migrations
- [ ] Redis for distributed rate limiting

### Observability

- [ ] OTel Collector deployment
- [ ] Grafana dashboards — Tempo traces, Loki logs, Prometheus metrics
- [ ] AlertManager rules on business metrics

### Integration

- [ ] Kong API Gateway routing
- [ ] Keycloak / JWT inter-service auth
- [ ] RabbitMQ async events (patient created, status changed)

### Platform

- [ ] Staging and production namespace deployments
- [ ] ArgoCD GitOps
- [ ] Helm chart

---

## Role in the Platform

patient-service (identity source of truth)
├── consumed by → appointment-service     (eligibility checks before booking)
├── consumed by → clinical-service        (patient context for clinical records)
├── consumed by → notification-service    (patient contact preferences)
├── consumed by → billing-service         (patient identity for invoicing)
├── consumed by → scheduling-service      (patient identity for slot allocation)
├── consumed by → provider-service        (patient-provider relationship)
├── consumed by → facility-service        (patient-facility assignment)
├── consumed by → support-service         (patient identity for helpdesk tickets)
├── simulated by → BioMeshSim             (synthetic patient traffic generation)
└── stress-tested by → BioMeshChaos       (chaos injection against patient endpoints)


BioMeshSim and BioMeshChaos are separate repositories and namespaces.
They interact with patient-service externally — they do not depend on its internals.
---

## Related Documentation

- `docs/patient-service-operator-guide.md` — full curl reference for local operation
- `docs/decisions/` — Architecture Decision Records
- `docs/runbooks/` — Kubernetes failure drill runbooks