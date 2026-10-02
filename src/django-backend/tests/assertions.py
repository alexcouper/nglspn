from datetime import timedelta
from http.cookies import Morsel

from django.conf import settings
from django.http import HttpResponse
from hamcrest import assert_that, equal_to, has_entries, has_key, not_


def refresh_cookie(response: HttpResponse) -> Morsel:
    """The refresh-token `Set-Cookie` on `response`, as a Morsel."""
    assert_that(response.cookies, has_key(settings.REFRESH_COOKIE_NAME))
    return response.cookies[settings.REFRESH_COOKIE_NAME]


def assert_sets_refresh_cookie(response: HttpResponse, *, secure: bool = True) -> None:
    idle_lifetime = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    cookie = refresh_cookie(response)

    assert_that(cookie.value, not_(equal_to("")))
    assert_that(
        cookie,
        has_entries(
            {
                "httponly": True,
                "samesite": "Lax",
                "path": "/api/auth",
                "max-age": idle_lifetime.total_seconds(),
                "secure": True if secure else "",
                # Host-only: no Domain attribute.
                "domain": "",
            }
        ),
    )


def assert_clears_refresh_cookie(response: HttpResponse) -> None:
    cookie = refresh_cookie(response)

    assert_that(cookie.value, equal_to(""))
    assert_that(cookie, has_entries({"path": "/api/auth", "max-age": 0}))


def assert_leaves_refresh_cookie_alone(response: HttpResponse) -> None:
    assert_that(response.cookies, not_(has_key(settings.REFRESH_COOKIE_NAME)))
