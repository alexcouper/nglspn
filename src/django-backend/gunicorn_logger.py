"""Custom gunicorn logger for structured JSON access logs."""

import logging
from datetime import timedelta
from typing import Any

from gunicorn.glogging import Logger as GunicornLogger


class StructuredLogger(GunicornLogger):
    """Gunicorn logger that emits structured access logs with queryable fields.

    Instead of the default Apache combined format string, this emits each
    access log field (method, url, ip, status, etc.) as a separate JSON key
    so they are individually queryable in Grafana/Loki.

    Kube-probe and health-check requests are dropped entirely.
    """

    def access(
        self,
        resp: Any,
        req: Any,
        environ: dict[str, str],
        request_time: timedelta,
    ) -> None:
        if not (self.cfg.accesslog is not None and self.cfg.accesslog != "None"):
            return

        user_agent = environ.get("HTTP_USER_AGENT", "")
        if "kube-probe" in user_agent:
            return

        path = environ.get("PATH_INFO", "")
        if path == "/health":
            return

        access_logger = logging.getLogger("gunicorn.access")
        if not access_logger.isEnabledFor(logging.INFO):
            return

        method = environ.get("REQUEST_METHOD", "")
        query = environ.get("QUERY_STRING", "")
        ip = environ.get("REMOTE_ADDR", "")

        status = None
        try:
            status = resp.status
            if isinstance(status, str):
                status = int(status.split(None, 1)[0])
        except (ValueError, TypeError):
            pass

        request_time_ms = int(request_time.total_seconds() * 1000)

        url = f"{path}?{query}" if query else path

        access_logger.info(
            "%s %s %s",
            method,
            url,
            status,
            extra={
                "method": method,
                "url": path,
                "query": query,
                "ip": ip,
                "status": status,
                "user_agent": user_agent,
                "response_length": getattr(resp, "sent", None),
                "request_time_ms": request_time_ms,
            },
        )
