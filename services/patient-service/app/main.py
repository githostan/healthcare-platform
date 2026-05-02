

# =============================================================================
# FastAPI application providing patient identity and profile
# =============================================================================
# - Patient Service API — FastAPI microservice providing patient identity and profile
# management with structured logging, API‑key authentication, Prometheus metrics,
# pagination metadata, soft‑delete lifecycle handling, audit logging, and full
# correlation/request ID propagation across all routes.

# - This module bootstraps the application: configures logging, initializes the
# repository and service layer, registers middleware, mounts all routers, and
# generates a custom OpenAPI schema with API‑key security definitions.

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.logging_config import configure_logging, get_logger
from app.middleware.request_context import RequestContextMiddleware
from app.repositories.patient_repository import InMemoryPatientRepository
from app.routes.health import router as health_router
from app.routes.meta import router as meta_router
from app.routes.metrics import router as metrics_router
from app.routes.patients import router as patients_router
from app.services.patient_service import PatientService

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
app.add_middleware(RequestContextMiddleware, logger=logger)

app.include_router(health_router)
app.include_router(meta_router)
app.include_router(metrics_router)
app.include_router(patients_router)


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