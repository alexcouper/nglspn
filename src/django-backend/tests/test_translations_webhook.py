from unittest.mock import patch

from hamcrest import assert_that, equal_to

from apps.translations.webhooks import notify_web_ui


class TestNotifyWebUi:
    def test_posts_to_configured_url_with_secret_header(self, settings) -> None:
        settings.WEB_UI_REVALIDATE_URL = "https://web.example/api/revalidate-i18n"
        settings.WEB_UI_REVALIDATE_SECRET = "top-secret"  # noqa: S105

        with patch("apps.translations.webhooks.requests.post") as post:
            post.return_value.status_code = 200
            notify_web_ui("is")

        post.assert_called_once()
        args = post.call_args.args
        kwargs = post.call_args.kwargs
        assert_that(args[0], equal_to("https://web.example/api/revalidate-i18n"))
        assert_that(kwargs["json"], equal_to({"locale": "is"}))
        assert_that(
            kwargs["headers"],
            equal_to({"X-Revalidate-Secret": "top-secret"}),
        )

    def test_no_op_when_url_unset(self, settings) -> None:
        settings.WEB_UI_REVALIDATE_URL = ""
        with patch("apps.translations.webhooks.requests.post") as post:
            notify_web_ui("is")
        post.assert_not_called()

    def test_swallows_network_errors(self, settings) -> None:
        settings.WEB_UI_REVALIDATE_URL = "https://web.example/api/revalidate-i18n"
        settings.WEB_UI_REVALIDATE_SECRET = "top-secret"  # noqa: S105
        with patch(
            "apps.translations.webhooks.requests.post",
            side_effect=Exception("boom"),
        ):
            notify_web_ui("is")  # Must not raise.
