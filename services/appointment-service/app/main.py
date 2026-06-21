# =============================================================================
# Appointment API — FastAPI application entrypoint
# =============================================================================
# NOTE (Purpose):
# - Slim wiring layer: constructs the FastAPI app, registers middleware,
#   includes the v1 API router, and manages startup/shutdown via lifespan.
# - All business logic, routing, auth, and observability concerns live in
#   their respective app/ subpackages — this file only assembles them.
# - Repository and service instances are created fresh per app instance
#   inside lifespan(), not as module-level singletons — keeps tests
#   isolated (each TestClient gets its own repository).
# - UI (Jinja2 templates, static assets) intentionally removed — see
#   ADR / commit history. A consolidated BioMeshCore frontend is planned;
#   this also closes the Starlette StaticFiles attack surface flagged
#   during patient-service's Phase 2 CVE review.

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.middleware.request_context import RequestContextMiddleware
from app.repositories.appointment_repository import InMemoryAppointmentRepository
from app.services.appointment_service import AppointmentService

configure_logging(settings.log_level)
logger = get_logger("appointment_api")

tags_metadata = [
    {"name": "Health", "description": "Liveness and readiness probes"},
    {"name": "Meta", "description": "Service metadata"},
    {"name": "Appointments", "description": "Appointment management APIs"},
    {"name": "Observability", "description": "Metrics and monitoring endpoints"},
    {"name": "Lab", "description": "Development-only runtime testing endpoints"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Repository and service are created per app instance here, not at
    # module import time — this is what keeps pytest test clients isolated
    # from each other (each TestClient triggers its own lifespan).
    repository = InMemoryAppointmentRepository()
    service = AppointmentService(repository=repository, logger=logger)

    app.state.appointment_repository = repository
    app.state.appointment_service = service
    app.state.startup_complete = True

    logger.info("startup_complete", extra={"service": settings.service_name})

    yield

    logger.info("shutdown", extra={"service": settings.service_name})


app = FastAPI(
    title="Appointment API",
    version=settings.service_version,
    openapi_tags=tags_metadata,
    openapi_version="3.0.3",
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=lifespan,
)

# NOTE: Middleware registration order matters. RequestContextMiddleware
# must be added here, before any OTel instrumentation is introduced in
# the observability branch — Starlette applies middleware in reverse
# registration order, so adding OTel after this will make OTel the
# outermost layer, ensuring trace IDs are non-zero in request_complete
# logs. See patient-service's Phase 2 middleware ordering decision.
app.add_middleware(RequestContextMiddleware)

app.include_router(api_router)


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
