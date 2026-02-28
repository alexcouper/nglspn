import pytest
from django.test import Client, override_settings
from hamcrest import assert_that, equal_to, is_not


@pytest.mark.django_db
class TestAdminIPMiddleware:
    @override_settings(ADMIN_ALLOWED_IPS=["10.0.0.1"])
    def test_admin_blocked_for_unknown_ip(self) -> None:
        client = Client()
        response = client.get("/admin/", REMOTE_ADDR="192.168.1.1")

        assert_that(response.status_code, equal_to(404))

    @override_settings(ADMIN_ALLOWED_IPS=["10.0.0.1"])
    def test_admin_allowed_for_configured_ip(self) -> None:
        client = Client()
        response = client.get("/admin/", REMOTE_ADDR="10.0.0.1")

        # Should not be 404 (will be 302 redirect to login)
        assert_that(response.status_code, is_not(equal_to(404)))

    @override_settings(ADMIN_ALLOWED_IPS=["10.0.0.1"])
    def test_admin_uses_rightmost_xff_ip(self) -> None:
        client = Client()
        # Rightmost IP is the one added by trusted proxy
        response = client.get(
            "/admin/",
            REMOTE_ADDR="192.168.1.1",
            HTTP_X_FORWARDED_FOR="evil.ip, 10.0.0.1",
        )

        assert_that(response.status_code, is_not(equal_to(404)))

    @override_settings(ADMIN_ALLOWED_IPS=["10.0.0.1"])
    def test_admin_ignores_spoofed_first_xff(self) -> None:
        client = Client()
        # Attacker puts allowed IP first, but their real IP is rightmost
        response = client.get(
            "/admin/",
            REMOTE_ADDR="192.168.1.1",
            HTTP_X_FORWARDED_FOR="10.0.0.1, 192.168.99.99",
        )

        assert_that(response.status_code, equal_to(404))
