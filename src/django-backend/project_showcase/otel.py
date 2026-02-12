"""OpenTelemetry initialization for distributed tracing.

Imports are done lazily inside the function to avoid loading OpenTelemetry
packages when tracing is not configured.
"""
# ruff: noqa: PLC0415

import os

_initialized = False


def init_otel() -> None:
    """Initialize OpenTelemetry tracing if OTEL endpoint is configured.

    Safe to call multiple times - will only initialize once.
    """
    global _initialized  # noqa: PLW0603
    if _initialized:
        return

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {"service.name": os.environ.get("OTEL_SERVICE_NAME", "django-backend")}
    )
    provider = TracerProvider(resource=resource)

    # Strip /v1/traces suffix if present - we add it explicitly below
    endpoint = endpoint.removesuffix("/v1/traces")
    exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Ensure Django is set up before instrumenting it
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_showcase.settings")
    django.setup()

    DjangoInstrumentor().instrument(excluded_urls="^/$,^/api/health$")
    Psycopg2Instrumentor().instrument(enable_commenter=True)

    # Also instrument sqlite3 for local development
    try:
        from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor

        SQLite3Instrumentor().instrument()
    except ImportError:
        pass  # sqlite3 instrumentor not installed

    _initialized = True
