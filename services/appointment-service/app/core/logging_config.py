# =============================================================================
# Structured JSON logging configuration for appointment-service
# =============================================================================
# NOTE (Purpose):
# - Replaces the ad-hoc logger setup previously inline in main.py.
# - Emits structured JSON log lines to stdout for container log aggregation.
# - Provides a consistent JsonFormatter usable by all loggers in the service.
# - trace_id/span_id/trace_sampled fields are placeholders here — populated
#   for real once OpenTelemetry is wired in during the observability phase.

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class TraceContextFilter(logging.Filter):
    """
    Phase 2 scaffold.
    Later this can inject OpenTelemetry trace_id/span_id into every log record.
    For now, keep fields present but unset.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = getattr(record, "trace_id", None)
        record.span_id = getattr(record, "span_id", None)
        record.trace_sampled = getattr(record, "trace_sampled", False)
        return True


class JsonFormatter(logging.Formatter):
    RESERVED = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge extra fields passed via logger.info("msg", extra={...})
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(log_level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(TraceContextFilter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level.upper())

    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
