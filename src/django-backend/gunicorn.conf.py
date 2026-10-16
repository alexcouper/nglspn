"""Gunicorn configuration for production."""

from gunicorn_logger import StructuredLogger

# Server socket
bind = "0.0.0.0:8000"

# Worker timeout — OTEL + Django init can exceed the 30s default on constrained CPUs
timeout = 120

# Custom logger class: structured JSON fields, filters kube-probe + health checks
logger_class = StructuredLogger
accesslog = "-"
errorlog = "-"

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
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
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
