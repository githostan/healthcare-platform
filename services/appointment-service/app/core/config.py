
# =============================================================================
# Centralised configuration for appointment-service
# =============================================================================
# NOTE (Purpose):
# - Single source of truth for all runtime configuration.
# - Uses Pydantic Settings for automatic environment variable binding,
#   type coercion, and validation at startup.
# - All configuration is read-only after startup — no mutable globals.
# - Fail-fast on missing required values (APPOINTMENT_SERVICE_API_KEY).

from __future__ import annotations

from typing import Literal

from pydantic import Field, conint, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Service identity ────────────────────────────────────────────
    service_name: str = Field(default="appointment-service", alias="SERVICE_NAME")
    service_version: str = Field(default="0.2.0", alias="SERVICE_VERSION")
    environment: Literal["dev", "staging", "prod"] = Field(
        default="dev",
        alias="ENVIRONMENT",
    )

    # ── Security ────────────────────────────────────────────────────
    appointment_service_api_key: str = Field(
        ...,
        alias="APPOINTMENT_SERVICE_API_KEY",
    )

    # ── Logging ─────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )

    # ── Pagination ──────────────────────────────────────────────────
    default_page_size: conint(ge=1, le=100) = Field(
        default=20,
        alias="DEFAULT_PAGE_SIZE",
    )
    max_page_size: conint(ge=1, le=500) = Field(
        default=100,
        alias="MAX_PAGE_SIZE",
    )

    # ── Rate limiting ────────────────────────────────────────────────
    rate_limit_per_minute: conint(ge=1, le=10000) = Field(
        default=60,
        alias="RATE_LIMIT_PER_MINUTE",
    )

    # ── Feature flags ────────────────────────────────────────────────
    enable_seed_data: bool = Field(default=False, alias="ENABLE_SEED_DATA")
    enable_lab_endpoints: bool = Field(default=False, alias="ENABLE_LAB_ENDPOINTS")

    # ── k8s downward API ────────────────────────────────────────────
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