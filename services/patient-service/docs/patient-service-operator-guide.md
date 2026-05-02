

# Patient Service — Operator Guide

A practical reference for running, testing, and operating `patient-service` locally.

---

## Start the Service

From `services/patient-service/`:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

---

## Environment Configuration

Local `.env` file (never commit this):

```dotenv
PATIENT_SERVICE_API_KEY=<your-api-key>
ENVIRONMENT=dev
LOG_LEVEL=INFO
ENABLE_SEED_DATA=true
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
RATE_LIMIT_PER_MINUTE=60
```

All protected endpoints require this header:

```
X-API-Key: <your-api-key>
```

---

## Health Endpoints

No API key required.

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/readyz
curl http://127.0.0.1:8000/startupz
curl http://127.0.0.1:8000/info
```

---

## Metrics Endpoint

```bash
curl -H "X-API-Key: <your-api-key>" \
  http://127.0.0.1:8000/metrics
```

---

## Generate Valid NHS Numbers

Single number:

```bash
PYTHONPATH=. python3 - <<'PY'
from app.utils.nhs import generate_valid_nhs_number
print(generate_valid_nhs_number())
PY
```

Generate 20 numbers:

```bash
PYTHONPATH=. python3 - <<'PY'
from app.utils.nhs import generate_valid_nhs_number
for _ in range(20):
    print(generate_valid_nhs_number())
PY
```

---

## Generate Fake Patients

Print to terminal:

```bash
PYTHONPATH=. python3 scripts/generate_patients.py
```

Save to file:

```bash
PYTHONPATH=. python3 scripts/generate_patients.py > patients.json
```

---

## List Patients

Default — active patients only:

```bash
curl -H "X-API-Key: <your-api-key>" \
  http://127.0.0.1:8000/api/v1/patients
```

Include inactive patients:

```bash
curl -H "X-API-Key: <your-api-key>" \
  "http://127.0.0.1:8000/api/v1/patients?include_inactive=true"
```

Filter by status:

```bash
curl -H "X-API-Key: <your-api-key>" \
  "http://127.0.0.1:8000/api/v1/patients?status=ACTIVE"
```

Filter by practice code:

```bash
curl -H "X-API-Key: <your-api-key>" \
  "http://127.0.0.1:8000/api/v1/patients?registered_practice_code=L83120"
```

Pagination:

```bash
curl -H "X-API-Key: <your-api-key>" \
  "http://127.0.0.1:8000/api/v1/patients?page=1&size=5"
```

---

## Create Patient

> Use a valid NHS number from the generator above.
> Seed data already uses `9434765919` and `4857773456` — do not reuse these.

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/patients \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{
    "nhs_number": "REPLACE_WITH_VALID_NHS_NUMBER",
    "first_name": "Stan",
    "last_name": "Test",
    "date_of_birth": "1990-01-01",
    "gender": "MALE",
    "phone": "07123456789",
    "email": "stan.test@example.com",
    "preferred_contact_method": "SMS",
    "registered_practice_code": "L83120",
    "status": "ACTIVE"
  }';echo
```

Expected success (`201 Created`):

```json
{
  "id": "...",
  "nhs_number": "...",
  "first_name": "Stan",
  "last_name": "Test",
  "status": "ACTIVE",
  "created_at": "...",
  "updated_at": "..."
}
```

Expected duplicate error (`409 Conflict`):

```json
{"detail": "Patient NHS number already exists"}
```

---

## Get Patient by ID

```bash
curl -H "X-API-Key: <your-api-key>" \
  http://127.0.0.1:8000/api/v1/patients/<patient_id>
```

---

## Get Patient by NHS Number

```bash
curl -H "X-API-Key: <your-api-key>" \
  http://127.0.0.1:8000/api/v1/patients/by-nhs-number/<nhs_number>
```

---

## Update Patient (Full Replacement)

All fields are required. This is a PUT — partial updates are not supported.

```bash
curl -s -X PUT http://127.0.0.1:8000/api/v1/patients/<patient_id> \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{
    "nhs_number": "REPLACE_WITH_VALID_NHS_NUMBER",
    "first_name": "Stanley",
    "last_name": "Updated",
    "date_of_birth": "1990-01-01",
    "gender": "MALE",
    "phone": "07999999999",
    "email": "stanley.updated@example.com",
    "preferred_contact_method": "EMAIL",
    "registered_practice_code": "L83120"
  }';echo
```

---

## Update Patient Status

Valid values: `ACTIVE`, `INACTIVE`

```bash
curl -s -X PATCH http://127.0.0.1:8000/api/v1/patients/<patient_id>/status \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{"status": "INACTIVE"}';echo
```

---

## Soft Delete Patient

Does not remove the record — sets status to `INACTIVE`.

```bash
curl -s -X DELETE \
  -H "X-API-Key: <your-api-key>" \
  http://127.0.0.1:8000/api/v1/patients/<patient_id>
```

Expected: `204 No Content` (empty response body)

Confirm the patient is now inactive:

```bash
curl -H "X-API-Key: <your-api-key>" \
  "http://127.0.0.1:8000/api/v1/patients?include_inactive=true"
```

---

## Check Booking Eligibility

Returns eligibility without requiring the patient to exist.

```bash
curl -H "X-API-Key: <your-api-key>" \
  http://127.0.0.1:8000/api/v1/patients/<patient_id>/eligibility
```

Active patient:

```json
{
  "patient_id": "...",
  "exists": true,
  "status": "ACTIVE",
  "eligible_for_booking": true
}
```

Inactive patient:

```json
{
  "patient_id": "...",
  "exists": true,
  "status": "INACTIVE",
  "eligible_for_booking": false
}
```

Patient not found:

```json
{
  "patient_id": "...",
  "exists": false,
  "status": null,
  "eligible_for_booking": false
}
```

---

## Swagger UI

Interactive API docs — try all endpoints in the browser:

```
http://127.0.0.1:8000/docs
```

Click **Authorize** and enter your API key before making requests.

---

## Common Errors

| Status | Detail                        | Cause                           | Fix                             |
|--------|-------------------------------|---------------------------------|---------------------------------|
| `401`  | Missing API key               | No `X-API-Key` header           | Add `-H "X-API-Key: ..."`       |
| `403`  | Invalid API key               | Wrong key value                 | Check `.env`                    |
| `404`  | Patient not found             | ID or NHS number does not exist | Verify the ID or NHS number     |
| `409`  | NHS number already exists     | Duplicate on create or update   | Generate a new valid NHS number |
| `422`  | Validation error              | Invalid field value or format   | See validation rules below      |
| `429`  | Rate limit exceeded           | Too many requests per minute    | Wait or increase the limit      |

### Common `422` Causes

- NHS number fails check digit validation
- `date_of_birth` is today or in the future
- Invalid `gender` — must be `MALE`, `FEMALE`, `OTHER`, or `UNKNOWN`
- Invalid `preferred_contact_method` — must be `SMS`, `EMAIL`, `PHONE`, or `NONE`
- Invalid email format
- Missing required field

---

## Rate Limiting

- Default: `60 requests per minute` per API key
- Configurable via `RATE_LIMIT_PER_MINUTE` in `.env`
- Exempt paths: `/healthz`, `/readyz`, `/startupz`, `/info`
- Exceeded limit returns `429 Too Many Requests`

---

## Seed Data

Loaded automatically on startup when `ENABLE_SEED_DATA=true`.

| NHS Number   | Name          | Status     |
|--------------|---------------|------------|
| `9434765919` | Ada Nwachukwu | `ACTIVE`   |
| `4857773456` | John Smith    | `INACTIVE` |

To disable seed data:

```dotenv
ENABLE_SEED_DATA=false
```

---

## Service Capabilities

`patient-service` currently supports:

- Patient creation with NHS number validation
- Patient lookup by ID
- Patient lookup by NHS number
- Patient listing with pagination
- Filtering by status (`ACTIVE` / `INACTIVE`)
- Filtering by registered practice code
- Full patient update (PUT)
- Status update (PATCH)
- Soft delete (sets status to `INACTIVE`)
- Booking eligibility check
- API key authentication (`401` / `403`)
- Per-request and correlation ID tracking
- Audit logging on all mutating operations
- Structured JSON logging with millisecond timestamps
- Prometheus metrics (`/metrics`)
- Valid NHS number generation utility
- Fake patient data generation script