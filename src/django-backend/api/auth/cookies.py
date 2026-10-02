"""The refresh-token cookie.

One place owns its name and attributes so that login, refresh and logout
cannot drift apart: a cookie is only replaced or expired by a `Set-Cookie`
with the same name and path. There is no `Domain`, which makes it host-only
for the API host.
"""

from datetime import timedelta

from django.conf import settings
from django.http import HttpRequest, HttpResponse


def set_refresh_cookie(response: HttpResponse, token: str) -> None:
    _write(
        response,
        token,
        max_age=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def clear_refresh_cookie(response: HttpResponse) -> None:
    _write(response, "", max_age=timedelta(0))


def read_refresh_cookie(request: HttpRequest) -> str | None:
    return request.COOKIES.get(settings.REFRESH_COOKIE_NAME) or None


def _write(response: HttpResponse, value: str, *, max_age: timedelta) -> None:
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        value,
        max_age=max_age,
        path=settings.REFRESH_COOKIE_PATH,
        secure=settings.REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite="Lax",
    )
