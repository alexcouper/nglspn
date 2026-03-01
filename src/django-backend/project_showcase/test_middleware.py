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

    @override_settings(ADMIN_ALLOWED_IPS=["10.0.0.1"], NUM_TRUSTED_PROXIES=1)
    def test_single_proxy_uses_rightmost_xff_entry(self) -> None:
        client = Client()
        response = client.get(
            "/admin/",
            REMOTE_ADDR="192.168.1.1",
            HTTP_X_FORWARDED_FOR="evil.ip, 10.0.0.1",
        )

        assert_that(response.status_code, is_not(equal_to(404)))

    @override_settings(ADMIN_ALLOWED_IPS=["10.0.0.1"], NUM_TRUSTED_PROXIES=1)
    def test_single_proxy_ignores_spoofed_first_xff(self) -> None:
        client = Client()
        response = client.get(
            "/admin/",
            REMOTE_ADDR="192.168.1.1",
            HTTP_X_FORWARDED_FOR="10.0.0.1, 192.168.99.99",
        )

        assert_that(response.status_code, equal_to(404))

    @override_settings(ADMIN_ALLOWED_IPS=["10.0.0.1"], NUM_TRUSTED_PROXIES=2)
    def test_two_proxies_skips_proxy_ip(self) -> None:
        client = Client()
        # Client(10.0.0.1) → CDN → LB → Django
        # CDN sets XFF: "10.0.0.1", LB appends: "10.0.0.1, <cdn_ip>"
        response = client.get(
            "/admin/",
            REMOTE_ADDR="192.168.1.1",
            HTTP_X_FORWARDED_FOR="10.0.0.1, 172.16.0.1",
        )

        assert_that(response.status_code, is_not(equal_to(404)))

    @override_settings(ADMIN_ALLOWED_IPS=["10.0.0.1"], NUM_TRUSTED_PROXIES=2)
    def test_two_proxies_ignores_spoofed_first_xff(self) -> None:
        client = Client()
        # Attacker spoofs XFF, so CDN appends real IP, LB appends CDN IP
        # XFF: <spoofed>, <real_client>, <cdn_ip>
        response = client.get(
            "/admin/",
            REMOTE_ADDR="192.168.1.1",
            HTTP_X_FORWARDED_FOR="10.0.0.1, 192.168.99.99, 172.16.0.1",
        )

        assert_that(response.status_code, equal_to(404))

    @override_settings(ADMIN_ALLOWED_IPS=["10.0.0.1"], NUM_TRUSTED_PROXIES=2)
    def test_fewer_xff_entries_than_proxies_uses_leftmost(self) -> None:
        client = Client()
        # Only 1 entry but NUM_TRUSTED_PROXIES=2, should clamp to index 0
        response = client.get(
            "/admin/",
            REMOTE_ADDR="192.168.1.1",
            HTTP_X_FORWARDED_FOR="10.0.0.1",
        )

        assert_that(response.status_code, is_not(equal_to(404)))
