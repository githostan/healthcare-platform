
# =============================================================================
# Structured JSON logging configuration
# =============================================================================
# NOTE (Purpose):
# - Implements a JSON-formatted logging pipeline for consistent, machine-
#   parseable logs across the service, suitable for ingestion by ELK, Loki,
#   Datadog, or any structured log aggregator.
# - Defines a custom `JsonFormatter` that emits stable, low-cardinality fields
#   including timestamp (UTC, millisecond precision), log level, logger name,
#   message, and optional request-scoped metadata injected by middleware.
# - Captures and serializes exception information (`exc_info`) and stack traces
#   (`stack_info`) to ensure operational visibility during failures without
#   relying on plain-text traceback output.
# - Configures the root logger with a single StreamHandler for predictable,
#   container-friendly output, using the service’s configured log level.
# - Exposes `get_logger()` for modules to obtain namespaced loggers that
#   integrate seamlessly with the JSON formatter and request context fields.

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for attr in (
            "request_id",
            "correlation_id",
            "action",
            "resource_type",
            "resource_id",
            "outcome",
            "method",
            "path",
            "status",
            "latency_ms",
            "api_key_fingerprint",
        ):
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)