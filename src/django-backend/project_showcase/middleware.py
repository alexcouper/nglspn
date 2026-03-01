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
            num_proxies: int = getattr(settings, "NUM_TRUSTED_PROXIES", 1)
            # Get client IP from X-Forwarded-For (set by proxies) or fall back
            # to REMOTE_ADDR. Count back from the right by NUM_TRUSTED_PROXIES
            # to skip trusted proxy IPs and land on the real client IP, which
            # also prevents spoofing via client-controlled left entries.
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                parts = x_forwarded_for.split(",")
                index = max(len(parts) - num_proxies, 0)
                client_ip = parts[index].strip()
            else:
                client_ip = request.META.get("REMOTE_ADDR", "")
            if client_ip not in allowed_ips:
                raise Http404

        return self.get_response(request)
