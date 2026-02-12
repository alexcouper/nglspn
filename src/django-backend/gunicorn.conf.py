"""Gunicorn configuration for production."""

import logging

# Server socket
bind = "0.0.0.0:8000"

# Worker timeout — OTEL + Django init can exceed the 30s default on constrained CPUs
timeout = 120

# Logging - use logconfig_dict for JSON structured logs
accesslog = "-"
errorlog = "-"


class HealthCheckFilter(logging.Filter):
    """Filter out health check requests from access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return "GET /health" not in message


# JSON logging configuration for Grafana/Cockpit filtering
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "filters": {
        "health_check": {
            "()": HealthCheckFilter,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["health_check"],
        },
        "error_console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "gunicorn.access": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn.error": {
            "handlers": ["error_console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Trust X-Forwarded-* headers from all IPs (required when behind load balancer/proxy)
# Cloud Run always sits behind a proxy, so we trust all forwarded IPs
forwarded_allow_ips = "*"


def post_fork(server, worker) -> None:  # noqa: ANN001
    """Initialize OpenTelemetry in each worker process after fork."""
    del server, worker  # unused but required by gunicorn
    from project_showcase.otel import init_otel  # noqa: PLC0415

    init_otel()
