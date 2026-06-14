
# =============================================================================
# Application configuration (typed, validated, environment-driven settings)
# =============================================================================
# NOTE (Purpose):
# - Defines all service configuration using Pydantic Settings, providing
#   strongly-typed, validated, and environment-driven configuration values.
# - Loads settings from environment variables (with `.env` support) to ensure
#   consistent behaviour across local, dev, staging, and production deployments.
# - Enforces strict validation for environment, log level, pagination bounds,
#   and rate-limiting thresholds using Literal types and constrained integers.
# - Ensures secrets (e.g., PATIENT_SERVICE_API_KEY) are required at startup,
#   preventing accidental boot without mandatory credentials.
# - Includes a cross-field validator to guarantee that DEFAULT_PAGE_SIZE never
#   exceeds MAX_PAGE_SIZE, catching misconfiguration early.
# - Exposes a single `settings` instance for clean, dependency-free access
#   throughout the service.

from typing import Literal

from pydantic import Field, conint, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ── Service identity ──────────────────────────────────────────
    service_name: str = "patient-service"
    service_version: str = "0.1.0"
    environment: Literal["dev", "staging", "prod"] = Field(
        "dev", alias="ENVIRONMENT"
    )

    # ── Security ──────────────────────────────────────────────────
    patient_service_api_key: str = Field(..., alias="PATIENT_SERVICE_API_KEY")

    # ── Feature flags ─────────────────────────────────────────────
    enable_seed_data: bool = Field(True, alias="ENABLE_SEED_DATA")

    # ── Pagination ────────────────────────────────────────────────
    default_page_size: conint(ge=1, le=100) = Field(20, alias="DEFAULT_PAGE_SIZE")
    max_page_size: conint(ge=1, le=500) = Field(100, alias="MAX_PAGE_SIZE")

    # ── Rate limiting ─────────────────────────────────────────────
    rate_limit_per_minute: conint(ge=1, le=10000) = Field(
        60, alias="RATE_LIMIT_PER_MINUTE"
    )

    # ── Logging ───────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", alias="LOG_LEVEL"
    )

    # ── OpenTelemetry ─────────────────────────────────────────────
    otel_enabled: bool = Field(
        default=True,
        alias="OTEL_ENABLED",
    )
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
        description=(
            "OTLP endpoint for the OTel Collector. "
            "When unset, ConsoleSpanExporter is active (pre-observability mode). "
            "gRPC: http://otel-collector.observability.svc.cluster.local:4317 "
            "HTTP: http://otel-collector.observability.svc.cluster.local:4318"
        ),
    )
    otel_exporter_protocol: Literal["grpc", "http"] = Field(
        default="grpc",
        alias="OTEL_EXPORTER_PROTOCOL",
    )
    otel_sampling_ratio: float = Field(
        default=1.0,
        alias="OTEL_SAMPLING_RATIO",
        ge=0.0,
        le=1.0,
    )

    # ── Kubernetes Downward API ───────────────────────────────────
    # Injected automatically by deployment.yml via fieldRef.
    # Set manually in .env for local development only.
    k8s_namespace: str = Field(default="healthcare-dev", alias="K8S_NAMESPACE")
    k8s_pod_name: str = Field(default="unknown", alias="K8S_POD_NAME")
    k8s_node_name: str = Field(default="unknown", alias="K8S_NODE_NAME")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def validate_pagination(self):
        if self.default_page_size > self.max_page_size:
            raise ValueError("DEFAULT_PAGE_SIZE cannot exceed MAX_PAGE_SIZE")
        return self


settings = Settings()