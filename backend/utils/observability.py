import logging
import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger(__name__)


def setup_observability(app: FastAPI, service_name: str, version: str):
    """
    Configure OpenTelemetry and Prometheus instrumentation.
    """
    env = os.getenv("ENVIRONMENT", "development")

    # 1. Prometheus Instrumentation
    try:
        instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=[".*admin.*", "/health", "/ready", "/metrics"],
            env_var_name="ENABLE_METRICS",
        )
        instrumentator.instrument(app).expose(app, endpoint="/metrics", tags=["health"])
        logger.info("Prometheus instrumentation initialized at /metrics")
    except Exception as e:
        logger.error(f"Failed to initialize Prometheus instrumentation: {e}")

    # 2. OpenTelemetry Tracing (GCP focused)
    try:
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": version,
                "deployment.environment": env,
            }
        )

        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        # In actual GCP environment, we would use CloudTraceSpanExporter
        # For local dev or if configured, we could use OTLP or Console exporter
        if os.getenv("ENABLE_TRACING", "false").lower() == "true":
            # Placeholder for GCP Trace Exporter
            # from opentelemetry.exporter.gcp_trace import CloudTraceSpanExporter
            # from opentelemetry.sdk.trace.export import BatchSpanProcessor
            # exporter = CloudTraceSpanExporter()
            # provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OpenTelemetry Tracing enabled")

        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        logger.info("OpenTelemetry FastAPI instrumentation initialized")

    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
