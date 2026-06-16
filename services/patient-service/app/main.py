# =============================================================================
# FastAPI application providing patient identity and profile
# =============================================================================
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.core.telemetry import configure_telemetry
from app.middleware.request_context import RequestContextMiddleware
from app.repositories.patient_repository import InMemoryPatientRepository
from app.services.patient_service import PatientService
from app.api.v1.health import router as health_router
from app.api.v1.meta import router as meta_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.patients import router as patients_router

configure_logging()
logger = get_logger("patient_service")

tags_metadata = [
    {"name": "Health", "description": "Liveness, readiness, and startup probes"},
    {"name": "Meta", "description": "Service metadata"},
    {"name": "Patients", "description": "Patient management APIs"},
    {"name": "Observability", "description": "Metrics and monitoring endpoints"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("patient-service starting")
    repository = InMemoryPatientRepository()
    service = PatientService(repository=repository, logger=logger)
    if settings.enable_seed_data:
        service.seed_data()
    app.state.patient_service = service
    app.state.startup_complete = True
    logger.info("patient-service startup complete")
    try:
        yield
    finally:
        app.state.startup_complete = False
        logger.info("patient-service shutting down")


app = FastAPI(
    title="Patient Service API",
    version=settings.service_version,
    openapi_tags=tags_metadata,
    openapi_version="3.0.3",
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=lifespan,
)

app.state.startup_complete = False

# Register RequestContextMiddleware FIRST
# Starlette reverses order — last registered = outermost
app.add_middleware(RequestContextMiddleware, logger=logger)

# configure_telemetry LAST — adds OpenTelemetryMiddleware as outermost
# Execution order becomes:
#   Request: OpenTelemetryMiddleware → RequestContextMiddleware → route
#   Response: route → RequestContextMiddleware → OpenTelemetryMiddleware
# request_complete fires while OTel span is still active → real trace IDs
configure_telemetry(app, settings)

app.include_router(health_router)
app.include_router(meta_router)
app.include_router(metrics_router)
app.include_router(patients_router, prefix="/api/v1")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        tags=tags_metadata,
    )
    openapi_schema.setdefault("components", {})
    openapi_schema["components"].setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"].setdefault(
        "APIKeyHeader",
        {"type": "apiKey", "in": "header", "name": "X-API-Key"},
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
