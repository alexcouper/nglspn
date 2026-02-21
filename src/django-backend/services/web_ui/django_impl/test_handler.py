import json
from unittest.mock import patch

import pytest

from services.web_ui.django_impl import DjangoWebUIHandler

handler = DjangoWebUIHandler()

URLOPEN = "services.web_ui.django_impl.handler.urllib.request.urlopen"


class TestRevalidatePaths:
    def test_sends_post_with_secret_and_paths(self, settings):
        settings.FRONTEND_URL = "https://example.com"
        settings.REVALIDATION_SECRET = "test-secret"  # noqa: S105

        with patch(URLOPEN) as mock:
            mock.return_value.__enter__ = lambda s: s
            mock.return_value.__exit__ = lambda s, *a: None
            mock.return_value.status = 200

            handler.revalidate_paths(["/", "/projects"])

            mock.assert_called_once()
            req = mock.call_args[0][0]
            assert req.full_url == "https://example.com/api/revalidate"
            assert req.method == "POST"
            assert req.get_header("Content-type") == "application/json"

    def test_does_not_raise_on_http_error(self, settings):
        settings.FRONTEND_URL = "https://example.com"
        settings.REVALIDATION_SECRET = "test-secret"  # noqa: S105

        with patch(
            URLOPEN,
            side_effect=Exception("connection refused"),
        ):
            handler.revalidate_paths(["/"])

    def test_skips_call_when_secret_is_empty(self, settings):
        settings.REVALIDATION_SECRET = ""

        with patch(URLOPEN) as mock:
            handler.revalidate_paths(["/"])

            mock.assert_not_called()

    @pytest.mark.parametrize("paths", [["/projects/abc"], ["/", "/projects"]])
    def test_request_body_contains_paths(self, settings, paths):
        settings.FRONTEND_URL = "https://example.com"
        settings.REVALIDATION_SECRET = "s3cret"  # noqa: S105

        with patch(URLOPEN) as mock:
            mock.return_value.__enter__ = lambda s: s
            mock.return_value.__exit__ = lambda s, *a: None
            mock.return_value.status = 200

            handler.revalidate_paths(paths)

            req = mock.call_args[0][0]
            body = json.loads(req.data)
            assert body["secret"] == "s3cret"  # noqa: S105
            assert body["paths"] == paths
