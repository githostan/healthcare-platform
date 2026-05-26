

# patient-service

A FastAPI microservice responsible for managing patient identity and profile data
within the Healthcare Platform.

---

## Overview

`patient-service` provides a clean, modular architecture with strong validation,
structured logging, observability, and API-key-based security. It is designed for
extensibility and production-readiness, with clear separation between API routes,
business logic, and data access layers.

---

## Current Status

| Area                | Status                                        |
|---------------------|-----------------------------------------------|
| API functionality   | ✅ Complete                                   |
| Auth (API key)      | ✅ Environment-based, timing-safe comparison  |
| NHS validation      | ✅ Modulus-11 check digit algorithm           |
| Observability       | ✅ Structured JSON logs + Prometheus metrics  |
| Rate limiting       | ✅ Per API key, sliding window                |
| Audit logging       | ✅ All mutating operations                    |
| CI/CD               | 🔜 Planned                                    |
| Dockerisation       | 🔜 Planned                                    |
| Deployment          | 🔜 Planned (k3s)                              |
| Persistent storage  | 🔜 PostgreSQL (planned)                       |

---

## Responsibilities

### Owns

- Patient lifecycle — creation, retrieval, update, soft delete
- NHS number validation (modulus-11 check digit)
- Patient eligibility checks for downstream services
- Source of truth for patient identity across the platform

### Does Not Own

- Appointment data — delegated to `appointment-service`
- Clinic data — delegated to `clinic-service` (future)
- Notifications — delegated to `notification-service` (future)

---

## Architecture

```
routes → services → repositories → models
```

| Layer          | Location                  | Responsibility                                        |
|----------------|---------------------------|-------------------------------------------------------|
| Routes         | `app/routes/`             | API endpoints, auth, request/response contracts       |
| Services       | `app/services/`           | Business logic, domain rules, audit logging           |
| Repositories   | `app/repositories/`       | Data access — currently in-memory, PostgreSQL planned |
| Schemas        | `app/schemas/`            | Pydantic models for validation and API contracts      |
| Middleware     | `app/middleware/`         | Request IDs, rate limiting, logging, metrics          |
| Config         | `app/config.py`           | Pydantic Settings — environment-driven configuration  |
| Utils          | `app/utils/`              | NHS number generation and validation                  |

---

## API Reference

### Health & Metadata

| Endpoint   | Description                          |
|------------|--------------------------------------|
| `/healthz` | Liveness probe                       |
| `/readyz`  | Readiness probe                      |
| `/startupz`| Startup completion probe             |
| `/info`    | Service metadata                     |
| `/metrics` | Prometheus metrics (API-key required)|

### Patients — `/api/v1/patients`

| Method   | Endpoint                          | Description                        |
|----------|-----------------------------------|------------------------------------|
| `GET`    | `/`                               | List patients (filterable, paged)  |
| `POST`   | `/`                               | Create a patient                   |
| `GET`    | `/{patient_id}`                   | Get patient by ID                  |
| `GET`    | `/by-nhs-number/{nhs_number}`     | Lookup patient by NHS number       |
| `PUT`    | `/{patient_id}`                   | Full patient update                |
| `PATCH`  | `/{patient_id}/status`            | Update status (`ACTIVE`/`INACTIVE`)|
| `DELETE` | `/{patient_id}`                   | Soft delete (sets to `INACTIVE`)   |
| `GET`    | `/{patient_id}/eligibility`       | Booking eligibility check          |

### Query Parameters — `GET /api/v1/patients`

| Parameter                   | Type      | Default  | Description                     |
|-----------------------------|-----------|----------|---------------------------------|
| `status`                    | `string`  | —        | Filter by `ACTIVE` or `INACTIVE`|
| `registered_practice_code`  | `string`  | —        | Filter by practice code         |
| `include_inactive`          | `bool`    | `false`  | Include inactive patients       |
| `page`                      | `int`     | `1`      | Page number (≥ 1)               |
| `size`                      | `int`     | `20`     | Page size (1–100)               |

---

## Authentication

All `/api/v1/*` endpoints require an API key header:

```
X-API-Key: <your-key>
```

Configured via environment variable:

```dotenv
PATIENT_SERVICE_API_KEY=replace-with-your-key
```

| Response | Cause               |
|----------|---------------------|
| `401`    | Missing API key     |
| `403`    | Invalid API key     |

---

## Configuration

All configuration is managed via environment variables using Pydantic Settings.

| Variable                  | Default  | Description                              |
|---------------------------|----------|------------------------------------------|
| `PATIENT_SERVICE_API_KEY` | required | API key for endpoint authentication      |
| `ENVIRONMENT`             | `dev`    | `dev` \| `staging` \| `prod`             |
| `LOG_LEVEL`               | `INFO`   | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR`|
| `ENABLE_SEED_DATA`        | `true`   | Load seed patients on startup            |
| `DEFAULT_PAGE_SIZE`       | `20`     | Default pagination page size             |
| `MAX_PAGE_SIZE`           | `100`    | Maximum pagination page size             |
| `RATE_LIMIT_PER_MINUTE`   | `60`     | Max requests per API key per minute      |

### `.env.example`

```dotenv
PATIENT_SERVICE_API_KEY=replace-with-your-key
ENVIRONMENT=dev
LOG_LEVEL=INFO
ENABLE_SEED_DATA=true
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
RATE_LIMIT_PER_MINUTE=60
```

> ⚠️ Never commit a real `.env` file. Copy `.env.example` to `.env` and fill in values locally.

---

## Running Locally

### 1. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set PATIENT_SERVICE_API_KEY
```

### 4. Start the service

```bash
uvicorn app.main:app --reload
```

Service available at: `http://127.0.0.1:8000`
Swagger UI at: `http://127.0.0.1:8000/docs`
redoc UI at: `http://127.0.0.1:8000/redoc`

---

## Example Requests

### Create Patient

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/patients \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-key>" \
  -d '{
    "nhs_number": "9434765919",
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-01-01",
    "gender": "MALE",
    "registered_practice_code": "L83120"
  }';echo
```

### List Patients

```bash
curl -H "X-API-Key: <your-key>" \
  "http://127.0.0.1:8000/api/v1/patients?status=ACTIVE&page=1&size=10"
```

### Check Eligibility

```bash
curl -H "X-API-Key: <your-key>" \
  http://127.0.0.1:8000/api/v1/patients/<patient_id>/eligibility
```

---

## Data Model

### Patient

| Field                      | Type                                        | Notes                        |
|----------------------------|---------------------------------------------|------------------------------|
| `id`                       | `string` (UUID)                             | Auto-generated               |
| `nhs_number`               | `string` (10 digits)                        | Modulus-11 validated, unique |
| `first_name`               | `string`                                    | 1–100 characters             |
| `last_name`                | `string`                                    | 1–100 characters             |
| `date_of_birth`            | `date`                                      | Must be in the past          |
| `gender`                   | `MALE`\|`FEMALE`\|`OTHER`\|`UNKNOWN`        |                              |
| `phone`                    | `string` \| `null`                          | Optional                     |
| `email`                    | `email` \| `null`                           | Optional, format validated   |
| `preferred_contact_method` | `SMS`\|`EMAIL`\|`PHONE`\|`NONE`             | Default: `NONE`              |
| `registered_practice_code` | `string`                                    | 3–20 characters              |
| `status`                   | `ACTIVE` \| `INACTIVE`                      | Default: `ACTIVE`            |
| `created_at`               | `datetime`                                  | UTC, set on creation         |
| `updated_at`               | `datetime`                                  | UTC, updated on every write  |

**Storage:** In-memory repository. Data is lost on restart. PostgreSQL planned.

---

## Observability

### Logging

- Structured JSON output with millisecond timestamps
- `request_id` and `correlation_id` on every log entry
- Audit logs on all mutating operations (create, update, delete)
- Exception tracebacks captured in JSON output

### Metrics

| Metric                          | Type      | Labels                        |
|---------------------------------|-----------|-------------------------------|
| `http_requests_total`           | Counter   | `method`, `path`, `status`    |
| `http_request_duration_seconds` | Histogram | `path`                        |

Accessible at `/metrics` (API-key required).

### Rate Limiting

- Sliding window — 60 requests per minute per API key (configurable)
- Exempt paths: `/healthz`, `/readyz`, `/startupz`, `/info`
- Returns `429 Too Many Requests` when exceeded

---

## NHS Number Validation

NHS numbers are validated using the modulus-11 check digit algorithm:

- Format enforced: exactly 10 ASCII digits (`^[0-9]{10}$`)
- Check digit verified against the modulus-11 algorithm
- Uniqueness enforced at create and update

Generate valid NHS numbers for development:

```bash
PYTHONPATH=. python3 - <<'PY'
from app.utils.nhs import generate_valid_nhs_number
for _ in range(10):
    print(generate_valid_nhs_number())
PY
```

---

## Seed Data

Loaded automatically on startup when `ENABLE_SEED_DATA=true`.

| NHS Number   | Name          | Status     |
|--------------|---------------|------------|
| `9434765919` | Ada Nwachukwu | `ACTIVE`   |
| `4857773456` | John Smith    | `INACTIVE` |

---

## Known Limitations

| Limitation                  | Notes                                              |
|-----------------------------|----------------------------------------------------|
| In-memory storage           | No persistence across restarts                     |
| Rate limiting               | Per-process only — not distributed across replicas |
| No service-to-service auth  | JWT / mTLS planned for inter-service calls         |

---

## Planned Evolution

### 🔜 Immediate

- [ ] Dockerfile
- [ ] CI/CD pipeline — lint, test, build, publish to GHCR
- [ ] Kubernetes deployment to k3s

### 🗄️ Data

- [ ] PostgreSQL integration via SQLAlchemy
- [ ] Alembic migrations (`platform/database/migrations/patient-service/`)
- [ ] Distributed rate limiting via Redis

### 🔗 Integration

- [ ] Service-to-service authentication (JWT / mTLS)
- [ ] API Gateway routing via Kong
- [ ] Shared Python libraries (`packages/python/healthcare-common`)

### 🎯 Platform

- [ ] Staging and production namespace deployments
- [ ] GitOps deployment via ArgoCD
- [ ] Helm chart (`platform/helm/patient-service/`)

---

## Role in the Platform

`patient-service` is the core identity service for the Healthcare Platform.

```
patient-service
    ├── consumed by → appointment-service (eligibility checks)
    ├── consumed by → clinic-service (future)
    └── consumed by → notification-service (future)
```

All services that need to act on a patient must validate eligibility through
`patient-service` before proceeding.

---

## Related Documentation

- `OPERATOR_GUIDE.md` — full curl command reference for local operation
- `docs/architecture/` — platform architecture decisions
- `docs/runbooks/` — Kubernetes failure drill runbooks