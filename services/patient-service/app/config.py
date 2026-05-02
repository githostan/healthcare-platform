
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
    service_name: str = "patient-service"
    service_version: str = "0.1.0"
    environment: Literal["dev", "staging", "prod"] = Field("dev", alias="ENVIRONMENT")

    patient_service_api_key: str = Field(..., alias="PATIENT_SERVICE_API_KEY")

    enable_seed_data: bool = Field(True, alias="ENABLE_SEED_DATA")

    default_page_size: conint(ge=1, le=100) = Field(20, alias="DEFAULT_PAGE_SIZE")
    max_page_size: conint(ge=1, le=500) = Field(100, alias="MAX_PAGE_SIZE")

    rate_limit_per_minute: conint(ge=1, le=10000) = Field(
        60, alias="RATE_LIMIT_PER_MINUTE"
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", alias="LOG_LEVEL"
    )

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