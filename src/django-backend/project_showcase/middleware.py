from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse


class AdminIPMiddleware:
    """Restrict /admin access to allowed IP addresses."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path.startswith("/admin"):
            allowed_ips: list[Any] = getattr(settings, "ADMIN_ALLOWED_IPS", [])
            # Get client IP from X-Forwarded-For (set by Scaleway) or fall back
            # to REMOTE_ADDR. Use rightmost IP (added by trusted proxy) to
            # prevent spoofing via client-controlled left entries.
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(",")[-1].strip()
            else:
                client_ip = request.META.get("REMOTE_ADDR", "")
            if client_ip not in allowed_ips:
                raise Http404

        return self.get_response(request)
