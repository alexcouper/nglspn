from django.http import HttpResponse
from django.test import RequestFactory
from hamcrest import assert_that, equal_to, is_, none

from api.auth.cookies import (
    clear_refresh_cookie,
    read_refresh_cookie,
    set_refresh_cookie,
)
from tests.assertions import (
    assert_clears_refresh_cookie,
    assert_sets_refresh_cookie,
    refresh_cookie,
)


def response_with_refresh_cookie(token):
    response = HttpResponse()
    set_refresh_cookie(response, token)
    return response


def request_with_cookies(**cookies):
    request = RequestFactory().post("/api/auth/refresh")
    request.COOKIES = cookies
    return request


class TestSetRefreshCookie:
    def test_carries_the_token(self):
        response = response_with_refresh_cookie("a-refresh-token")

        assert_that(refresh_cookie(response).value, equal_to("a-refresh-token"))

    def test_carries_every_attribute(self):
        assert_sets_refresh_cookie(response_with_refresh_cookie("a-refresh-token"))

    def test_is_not_secure_when_the_setting_is_off(self, settings):
        settings.REFRESH_COOKIE_SECURE = False

        assert_sets_refresh_cookie(
            response_with_refresh_cookie("a-refresh-token"), secure=False
        )


class TestClearRefreshCookie:
    def test_expires_the_cookie_under_the_same_name_and_path(self):
        response = HttpResponse()

        clear_refresh_cookie(response)

        assert_clears_refresh_cookie(response)


class TestReadRefreshCookie:
    def test_returns_the_token_that_was_set(self):
        request = request_with_cookies(refresh_token="a-refresh-token")

        assert_that(read_refresh_cookie(request), equal_to("a-refresh-token"))

    def test_returns_none_without_the_cookie(self):
        assert_that(read_refresh_cookie(request_with_cookies()), is_(none()))

    def test_returns_none_for_an_emptied_cookie(self):
        request = request_with_cookies(refresh_token="")

        assert_that(read_refresh_cookie(request), is_(none()))
