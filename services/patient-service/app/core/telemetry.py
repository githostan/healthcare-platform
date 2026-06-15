
# =============================================================================
# OpenTelemetry bootstrap for patient-service
# =============================================================================
# NOTE (Purpose):
# - Initialises the OTel TracerProvider with resource attributes, sampling,
#   and the appropriate span exporter based on environment configuration.
# - Configures W3C TraceContext and B3 propagation for broad compatibility
#   with upstream/downstream services and observability backends.
# - Auto-instruments FastAPI, httpx, and logging so traces are generated
#   with no further code changes as the platform grows.
# - When OTEL_EXPORTER_OTLP_ENDPOINT is not set, falls back to
#   ConsoleSpanExporter so instrumentation is always exercised locally.
# - All configuration is read from app.core.config.settings.
#
# Call configure_telemetry() once before FastAPI app creation in main.py.
#
# HTTP endpoint note:
#   Set OTEL_EXPORTER_OTLP_ENDPOINT to the base collector URL only.
#   Example: http://otel-collector.observability.svc.cluster.local:4318
#   The /v1/traces path suffix is appended automatically for HTTP protocol.
# =============================================================================

from __future__ import annotations

import logging

from fastapi import FastAPI

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPGrpcSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPHttpSpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.core.config import Settings

from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)


logger = logging.getLogger(__name__)


def configure_telemetry(app: FastAPI, settings: Settings) -> None:
    """
    Initialise OpenTelemetry for patient-service.

    Must be called before FastAPI app creation in main.py.
    Reads all configuration from app.core.config.settings.
    """
    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled via otel_enabled=false — skipping")
        return

    provider = TracerProvider(
        resource=_build_resource(settings),
        sampler=_build_sampler(settings),
    )
    exporter = _build_exporter(settings)
    
    if settings.otel_exporter_otlp_endpoint:
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Set provider globally BEFORE instrumenting libraries
    trace.set_tracer_provider(provider)

    _configure_propagators()
    _instrument_libraries(app)

    # Verify it stuck
    actual = trace.get_tracer_provider()
    logger.info(
        "OpenTelemetry initialised",
        extra={
            "service": settings.service_name,
            "environment": settings.environment,
            "otel_exporter_protocol": settings.otel_exporter_protocol,
            "otel_exporter_endpoint": settings.otel_exporter_otlp_endpoint or "console",
            "otel_sampling_ratio": settings.otel_sampling_ratio,
        },
    )


def _build_resource(settings: Settings) -> Resource:
    """
    Build OTel resource attributes attached to every span.

    k8s fields (namespace, pod, node) are injected via the downward
    API in deployment.yml — they identify exactly which pod generated
    a trace in a multi-replica deployment.
    """
    return Resource.create({
        "service.name": settings.service_name,
        "service.version": settings.service_version,
        "service.namespace": "biomeshcore",
        "deployment.environment": settings.environment,
        "k8s.namespace.name": settings.k8s_namespace,
        "k8s.pod.name": settings.k8s_pod_name,
        "k8s.node.name": settings.k8s_node_name,
    })


def _build_sampler(settings: Settings):
    """
    Configure trace sampling strategy.

    ParentBased: if an upstream caller is sampled, this service samples
    too — maintaining complete distributed trace chains across services.

    TraceIdRatioBased: root traces sampled at the configured ratio.
        1.0 = record every trace (dev default)
        0.1 = record 10% of traces (high-traffic production)
    """
    return ParentBased(
        root=TraceIdRatioBased(settings.otel_sampling_ratio)
    )


def _build_exporter(settings: Settings):
    """
    Build the appropriate span exporter based on environment config.

    No endpoint → ConsoleSpanExporter
        Traces print to stdout. Instrumentation is always exercised.
        This is the pre-Tempo development mode.

    Endpoint set → OTLP exporter to OTel Collector
        Collector routes spans to Tempo, metrics to Prometheus,
        logs to Loki. One env var switches behaviour — no code changes.

    insecure=True on gRPC:
        Internal k3s cluster traffic is not TLS terminated.
        Required for connections to the OTel Collector within the cluster.
    """
    endpoint = settings.otel_exporter_otlp_endpoint
    protocol = settings.otel_exporter_protocol

    if not endpoint:
        logger.info(
            "OTEL_EXPORTER_OTLP_ENDPOINT not set — "
            "ConsoleSpanExporter active (pre-observability mode)"
        )
        return ConsoleSpanExporter()

    if protocol == "http":
        logger.info("OTel exporter: OTLP HTTP → %s/v1/traces", endpoint)
        return OTLPHttpSpanExporter(
            endpoint=f"{endpoint}/v1/traces",
        )

    logger.info("OTel exporter: OTLP gRPC → %s", endpoint)
    return OTLPGrpcSpanExporter(
        endpoint=endpoint,
        insecure=True,
    )


def _configure_propagators() -> None:
    """
    Configure W3C TraceContext and B3 propagation.

    W3C TraceContext (traceparent header):
        Industry standard. Works with Tempo, Jaeger, Datadog, AWS X-Ray.

    B3 Multi-Format (X-B3-* headers):
        Zipkin compatible. Works with older proxies and some AWS services.

    Both active simultaneously — incoming requests parsed for either
    format, outgoing requests include both.
    """
    set_global_textmap(
        CompositePropagator([
            TraceContextTextMapPropagator(),
            B3MultiFormat(),
        ])
    )


def _instrument_libraries(app: FastAPI) -> None:
    """
    Auto-instrument all supported libraries.

    FastAPI   — SERVER spans for every inbound HTTP request.
    httpx     — CLIENT spans for every outbound service-to-service call.
    logging   — injects trace_id and span_id into every log record
                enabling Grafana log-to-trace correlation in Loki + Tempo.
    """
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=False)