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
# - Adds TraceContextFilter to inject OTel trace_id and span_id into every
#   log record — enabling Grafana log-to-trace correlation in Loki + Tempo.
# - Captures and serializes exception information (`exc_info`) and stack traces
#   (`stack_info`) to ensure operational visibility during failures without
#   relying on plain-text traceback output.
# - Configures the root logger with a single StreamHandler for predictable,
#   container-friendly output, using the service's configured log level.
# - Exposes `get_logger()` for modules to obtain namespaced loggers that
#   integrate seamlessly with the JSON formatter and request context fields.

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


class TraceContextFilter(logging.Filter):
    """
    Injects active OTel trace_id and span_id into every log record.

    When Loki and Tempo are both running, Grafana uses these fields
    to show a 'View Trace' button next to each log line — clicking it
    opens the correlated trace in Tempo.

    Outputs zeroed IDs when no active span exists (health probes,
    startup logs) so the fields are always present in log records —
    Loki expects a consistent schema across all records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx.is_valid:
                record.trace_id = format(ctx.trace_id, "032x")
                record.span_id = format(ctx.span_id, "016x")
                record.trace_sampled = ctx.trace_flags.sampled
            else:
                record.trace_id = "0" * 32
                record.span_id = "0" * 16
                record.trace_sampled = False
        except Exception:
            record.trace_id = "0" * 32
            record.span_id = "0" * 16
            record.trace_sampled = False
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Request context fields — injected by RequestContextMiddleware
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

        # OTel trace context fields — injected by TraceContextFilter
        for attr in ("trace_id", "span_id", "trace_sampled"):
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
    handler.addFilter(TraceContextFilter())
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
