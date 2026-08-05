from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from hamcrest import assert_that, contains_string, equal_to, has_length

from tests.factories import (
    ArticleFactory,
    DiscussionFactory,
    NotificationFactory,
    UserFactory,
)


@pytest.fixture
def admin_client() -> Client:
    admin_user = UserFactory(is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(admin_user)
    return client


def _unsent_discussion_notification(recipient=None):
    return NotificationFactory(
        recipient=recipient or UserFactory(),
        discussion=DiscussionFactory(),
        email_sent=False,
    )


def _unsent_article_notification(recipient=None):
    return NotificationFactory(
        recipient=recipient or UserFactory(),
        discussion=None,
        article=ArticleFactory(),
        email_sent=False,
    )


@pytest.mark.django_db
class TestPreviewDigestListView:
    def test_lists_recipients_with_both_kinds(self, admin_client):
        recipient = UserFactory()
        _unsent_discussion_notification(recipient=recipient)
        _unsent_article_notification(recipient=recipient)

        response = admin_client.get(
            reverse("admin:notifications_notification_preview_digest")
        )

        assert_that(response.status_code, equal_to(200))
        body = response.content.decode()
        assert_that(body, contains_string("<strong>2</strong> unsent"))
        assert_that(body, contains_string(">discussions<"))
        assert_that(body, contains_string(">articles<"))
        assert_that(body, contains_string(recipient.email))

    def test_handles_article_only_recipient(self, admin_client):
        _unsent_article_notification()

        response = admin_client.get(
            reverse("admin:notifications_notification_preview_digest")
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.content.decode(), contains_string("articles"))

    def test_excludes_already_sent_notifications(self, admin_client):
        sent = NotificationFactory(
            discussion=None, article=ArticleFactory(), email_sent=True
        )
        assert sent.email_sent

        response = admin_client.get(
            reverse("admin:notifications_notification_preview_digest")
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.content.decode(), contains_string("<strong>0</strong> unsent")
        )


@pytest.mark.django_db
class TestPreviewDigestDetailView:
    def test_renders_discussion_digest_html(self, admin_client):
        notification = _unsent_discussion_notification()

        response = admin_client.get(
            reverse(
                "admin:notifications_notification_preview_digest_detail",
                args=["discussion", notification.recipient_id],
            )
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.content.decode(),
            contains_string(notification.discussion.project.title),
        )

    def test_renders_article_digest_html(self, admin_client):
        notification = _unsent_article_notification()

        response = admin_client.get(
            reverse(
                "admin:notifications_notification_preview_digest_detail",
                args=["article", notification.recipient_id],
            )
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.content.decode(),
            contains_string(notification.article.title),
        )

    def test_renders_article_digest_text(self, admin_client):
        notification = _unsent_article_notification()

        response = admin_client.get(
            reverse(
                "admin:notifications_notification_preview_digest_detail",
                args=["article", notification.recipient_id],
            )
            + "?format=text"
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.content.decode(),
            contains_string(notification.article.title),
        )

    def test_unknown_kind_returns_404(self, admin_client):
        user = UserFactory()

        response = admin_client.get(
            reverse(
                "admin:notifications_notification_preview_digest_detail",
                args=["nonsense", user.id],
            )
        )

        assert_that(response.status_code, equal_to(404))

    def test_no_unsent_returns_empty_message(self, admin_client):
        user = UserFactory()

        response = admin_client.get(
            reverse(
                "admin:notifications_notification_preview_digest_detail",
                args=["article", user.id],
            )
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.content.decode(), contains_string("No unsent"))

    def test_discussion_view_ignores_article_notifications(self, admin_client):
        recipient = UserFactory()
        _unsent_article_notification(recipient=recipient)

        response = admin_client.get(
            reverse(
                "admin:notifications_notification_preview_digest_detail",
                args=["discussion", recipient.id],
            )
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.content.decode(), contains_string("No unsent"))
        assert_that(
            list(response.content.decode().split("No unsent")),
            has_length(2),
        )
