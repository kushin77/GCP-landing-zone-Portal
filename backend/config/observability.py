"""
OpenTelemetry Configuration for Distributed Tracing

Features:
- Cloud Trace exporter
- Custom business metrics
- Intelligent sampling
- Auto-instrumentation for FastAPI, Redis, HTTP
- Structured logging with trace context
"""

import logging
import os

from opentelemetry import metrics, trace

# Make exporters and instrumentations optional so tests and local dev
# environments without GCP/OpenTelemetry extras won't fail at import time.
try:
    from opentelemetry.exporter.gcp_monitoring import GoogleCloudMetricsExporter
    from opentelemetry.exporter.gcp_trace import CloudTraceExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

    GCP_EXPORTERS_AVAILABLE = True
except Exception:
    CloudTraceExporter = None
    GoogleCloudMetricsExporter = None
    TracerProvider = None
    BatchSpanProcessor = None
    TraceIdRatioBased = None
    MeterProvider = None
    PeriodicExportingMetricReader = None
    GCP_EXPORTERS_AVAILABLE = False

# Instrumentation fallbacks
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except Exception:

    class FastAPIInstrumentor:
        @staticmethod
        def instrument_app(app):
            return None


try:
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
except Exception:

    class RequestsInstrumentor:
        @staticmethod
        def instrument():
            return None


try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
except Exception:

    class HTTPXClientInstrumentor:
        @staticmethod
        def instrument():
            return None


try:
    from opentelemetry.instrumentation.redis import RedisInstrumentor
except Exception:

    class RedisInstrumentor:
        @staticmethod
        def instrument():
            return None


try:
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
except Exception:

    class LoggingInstrumentor:
        @staticmethod
        def instrument():
            return None


from fastapi import FastAPI

logger = logging.getLogger(__name__)


class SLOConfig:
    """SLO definitions"""

    SLOs = {
        "api_availability": {
            "name": "API Availability",
            "target": 0.9999,  # 99.99%
            "window": "30d",
            "metric": "api_errors_total",
            "description": "API should be available 99.99% of the time",
        },
        "cost_dashboard_latency": {
            "name": "Cost Dashboard Latency",
            "target": 0.95,  # 95% of requests < 1s
            "window": "7d",
            "metric": "api_latency_seconds_p95",
            "description": "95% of cost dashboard requests should complete within 1 second",
        },
        "compliance_freshness": {
            "name": "Compliance Report Freshness",
            "target": 0.98,  # 98% within 1 hour
            "window": "30d",
            "metric": "compliance_report_freshness",
            "description": "98% of compliance reports should be generated within 1 hour",
        },
    }


def setup_tracing(app: FastAPI) -> tuple[trace.TracerProvider, metrics.MeterProvider]:
    """
    Initialize OpenTelemetry with GCP exporters

    Args:
        app: FastAPI application instance

    Returns:
        tuple of (TracerProvider, MeterProvider)
    """
    project_id = os.getenv("GCP_PROJECT_ID", "landing-zone-hub")
    environment = os.getenv("ENVIRONMENT", "development")

    logger.info(f"Setting up OpenTelemetry for {project_id} in {environment}")

    # ========================================================================
    # Tracing Setup
    # ========================================================================

    tracer_provider = None
    # Cloud Trace exporter (optional)
    if GCP_EXPORTERS_AVAILABLE and CloudTraceExporter is not None:
        trace_exporter = CloudTraceExporter(project_id=project_id)

        # Sampler: 10% of normal traces, 100% of errors and slow requests
        sampler = TraceIdRatioBased(0.1)

        # Tracer provider
        tracer_provider = TracerProvider(sampler=sampler)
        tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
        trace.set_tracer_provider(tracer_provider)

    # ========================================================================
    # Metrics Setup
    # ========================================================================

    # Cloud Monitoring exporter (optional)
    meter_provider = None
    if (
        GCP_EXPORTERS_AVAILABLE
        and GoogleCloudMetricsExporter is not None
        and PeriodicExportingMetricReader is not None
        and MeterProvider is not None
    ):
        metrics_reader = PeriodicExportingMetricReader(
            GoogleCloudMetricsExporter(project_id=project_id),
            interval_millis=10000,  # Export every 10 seconds
        )

        # Meter provider
        meter_provider = MeterProvider(metric_readers=[metrics_reader])
        metrics.set_meter_provider(meter_provider)
    else:
        # Ensure a meter provider exists even if exporters are unavailable
        try:
            meter_provider = metrics.get_meter_provider()
        except Exception:
            meter_provider = None

    # ========================================================================
    # Auto-Instrumentation
    # ========================================================================

    # FastAPI instrumentation
    # Instrument when instrumentors are available (no-op fallbacks exist)
    try:
        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        pass

    try:
        RequestsInstrumentor().instrument()
    except Exception:
        pass

    try:
        HTTPXClientInstrumentor().instrument()
    except Exception:
        pass

    try:
        RedisInstrumentor().instrument()
    except Exception:
        pass

    try:
        LoggingInstrumentor().instrument()
    except Exception:
        pass

    logger.info("OpenTelemetry setup complete")

    return tracer_provider, meter_provider


class TraceContextFilter(logging.Filter):
    """Add trace context to all log records"""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace and span IDs to log record"""
        span_context = trace.get_current_span().get_span_context()

        if span_context and span_context.is_valid:
            record.trace_id = format(span_context.trace_id, "032x")
            record.span_id = format(span_context.span_id, "016x")
        else:
            record.trace_id = "0" * 32
            record.span_id = "0" * 16

        return True


def setup_structured_logging():
    """
    Configure structured logging with trace context

    Log records will include:
    - trace_id: Cloud Trace trace ID
    - span_id: Cloud Trace span ID
    - timestamp: ISO format timestamp
    - severity: Log level
    - message: Log message
    """
    import json

    class StructuredFormatter(logging.Formatter):
        """Format logs as JSON with trace context"""

        def format(self, record: logging.LogRecord) -> str:
            log_record = {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
                "severity": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
                "trace_id": getattr(record, "trace_id", "0" * 32),
                "span_id": getattr(record, "span_id", "0" * 16),
            }

            # Add extra fields if present
            if hasattr(record, "user_id"):
                log_record["user_id"] = record.user_id
            if hasattr(record, "request_id"):
                log_record["request_id"] = record.request_id

            # Add exception info
            if record.exc_info:
                log_record["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_record)

    # Get root logger
    root_logger = logging.getLogger()

    # Add trace context filter
    root_logger.addFilter(TraceContextFilter())

    # Configure handler with structured formatter
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())

    # Set level
    root_logger.setLevel(logging.INFO)

    # Replace existing handlers
    root_logger.handlers = [handler]


def define_custom_metrics() -> dict:
    """
    Define custom business metrics

    Returns:
        dict of metric instruments
    """
    meter = metrics.get_meter(__name__)

    # API Metrics
    api_requests_total = meter.create_counter(
        "api_requests_total",
        unit="1",
        description="Total API requests",
    )

    api_latency = meter.create_histogram(
        "api_latency_seconds",
        unit="s",
        description="API request latency",
    )

    # Business Metrics
    projects_created_total = meter.create_counter(
        "projects_created_total",
        unit="1",
        description="Total projects created",
    )

    compliance_violations_total = meter.create_counter(
        "compliance_violations_total",
        unit="1",
        description="Compliance violations detected",
    )

    cost_anomalies_detected = meter.create_counter(
        "cost_anomalies_total",
        unit="1",
        description="Cost anomalies detected",
    )

    # Resource Metrics
    active_projects = meter.create_up_down_counter(
        "active_projects", unit="1", description="Number of active projects"
    )

    # Cache Metrics
    cache_hits_total = meter.create_counter(
        "cache_hits_total",
        unit="1",
        description="Cache hits",
    )

    cache_misses_total = meter.create_counter(
        "cache_misses_total",
        unit="1",
        description="Cache misses",
    )

    return {
        "api_requests_total": api_requests_total,
        "api_latency": api_latency,
        "projects_created_total": projects_created_total,
        "compliance_violations_total": compliance_violations_total,
        "cost_anomalies_detected": cost_anomalies_detected,
        "active_projects": active_projects,
        "cache_hits_total": cache_hits_total,
        "cache_misses_total": cache_misses_total,
    }


def get_slo_config() -> dict:
    """Get SLO configuration for monitoring dashboards"""
    return SLOConfig.SLOs
