from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.follows.models import Follow, FollowedChannel
from apps.notifications.models import Notification, NotificationCadence
from apps.users.models import ArticleEmailFrequency
from services.articles.django_impl.handler import DjangoArticleHandler
from services.notifications.django_impl.handler import DjangoNotificationHandler
from tests.factories import (
    ArticleFactory,
    ChannelFactory,
    ProjectFactory,
    PublishedArticleFactory,
    UserFactory,
)


def _follow_channel(user, project, channel) -> Follow:
    """Set up `(user, project, channel)` follow.

    The model collapse means "is followed" is captured by row existence —
    no booleans to pass. A small helper keeps each call concise and avoids
    inventing factory plumbing for the (Follow, FollowedChannel) pair.
    """
    follow, _ = Follow.objects.get_or_create(user=user, project=project)
    FollowedChannel.objects.get_or_create(follow=follow, channel=channel)
    return follow


@pytest.mark.django_db
class TestCreateNotificationsForArticle:
    def setup_method(self):
        self.handler = DjangoNotificationHandler()

    def test_followed_channel_recipient_gets_in_app_row(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(article_email_frequency=ArticleEmailFrequency.HOURLY)
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)

        self.handler.create_notifications_for_article(article.id)

        row = Notification.objects.get(recipient=follower, article=article)
        assert row.in_app_read_at is None
        assert row.email_sent is False
        assert row.email_cadence == NotificationCadence.HOURLY

    def test_recipient_without_followed_channel_gets_nothing(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        # User has Follow on the project but no FollowedChannel — no row.
        user = UserFactory()
        Follow.objects.get_or_create(user=user, project=project)
        article = PublishedArticleFactory(project=project, channel=channel)

        self.handler.create_notifications_for_article(article.id)

        assert not Notification.objects.filter(recipient=user, article=article).exists()

    def test_recipient_on_never_still_gets_in_app_row(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(article_email_frequency=ArticleEmailFrequency.NEVER)
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)

        self.handler.create_notifications_for_article(article.id)

        row = Notification.objects.get(recipient=follower, article=article)
        assert row.email_cadence == NotificationCadence.NEVER
        assert row.email_sent is False
        assert row.in_app_read_at is None

    def test_author_excluded(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        author = project.creator
        _follow_channel(author, project, channel)
        article = PublishedArticleFactory(
            project=project, channel=channel, author=author
        )

        self.handler.create_notifications_for_article(article.id)

        assert not Notification.objects.filter(recipient=author).exists()

    def test_inactive_user_excluded(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(is_active=False)
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)

        self.handler.create_notifications_for_article(article.id)

        assert not Notification.objects.filter(recipient=follower).exists()

    def test_no_synchronous_email_at_fan_out(self):
        """Article fan-out NEVER fires immediate email — always digest path."""
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(article_email_frequency=ArticleEmailFrequency.HOURLY)
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_digest_email"
        ) as send_email:
            self.handler.create_notifications_for_article(article.id)

        send_email.assert_not_called()
        assert Notification.objects.filter(recipient=follower, article=article).exists()

    def test_snapshots_article_cadence_at_creation_time(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(article_email_frequency=ArticleEmailFrequency.WEEKLY)
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)

        self.handler.create_notifications_for_article(article.id)

        row = Notification.objects.get(recipient=follower, article=article)
        assert row.email_cadence == ArticleEmailFrequency.WEEKLY

    def test_idempotent_on_re_invoke(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)

        self.handler.create_notifications_for_article(article.id)
        self.handler.create_notifications_for_article(article.id)

        count = Notification.objects.filter(recipient=follower, article=article).count()
        assert count == 1

    def test_draft_article_is_no_op(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        _follow_channel(follower, project, channel)
        article = ArticleFactory(project=project, channel=channel)

        self.handler.create_notifications_for_article(article.id)

        assert not Notification.objects.filter(article=article).exists()

    def test_unknown_article_id_is_no_op(self):
        self.handler.create_notifications_for_article(uuid.uuid4())

    def test_backdate_gating_is_not_owned_here(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)
        article.published_at = timezone.now() - timedelta(days=30)
        article.save(update_fields=["published_at"])

        self.handler.create_notifications_for_article(article.id)

        assert Notification.objects.filter(recipient=follower, article=article).exists()


@pytest.mark.django_db
class TestMarkArticleReadForUser:
    def setup_method(self):
        self.handler = DjangoNotificationHandler()

    def test_marks_only_caller_rows(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        user_a = UserFactory()
        user_b = UserFactory()
        _follow_channel(user_a, project, channel)
        _follow_channel(user_b, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)
        self.handler.create_notifications_for_article(article.id)

        marked = self.handler.mark_article_read_for_user(user_a.id, article.id)

        assert marked == 1
        row_a = Notification.objects.get(recipient=user_a, article=article)
        row_b = Notification.objects.get(recipient=user_b, article=article)
        assert row_a.in_app_read_at is not None
        assert row_b.in_app_read_at is None

    def test_idempotent_on_already_read(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        user = UserFactory()
        _follow_channel(user, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)
        self.handler.create_notifications_for_article(article.id)
        self.handler.mark_article_read_for_user(user.id, article.id)

        marked = self.handler.mark_article_read_for_user(user.id, article.id)

        assert marked == 0

    def test_no_op_when_no_row_exists(self):
        user = UserFactory()
        marked = self.handler.mark_article_read_for_user(user.id, uuid.uuid4())
        assert marked == 0


@pytest.mark.django_db
class TestArticleDigest:
    def setup_method(self):
        self.handler = DjangoNotificationHandler()

    def test_hourly_digest_sends_email_and_marks_sent(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(article_email_frequency=ArticleEmailFrequency.HOURLY)
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)
        self.handler.create_notifications_for_article(article.id)

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_digest_email"
        ) as send_email:
            self.handler.send_article_digest("hourly")

        send_email.assert_called_once()
        row = Notification.objects.get(recipient=follower, article=article)
        assert row.email_sent is True

    def test_weekly_digest_picks_up_weekly_rows(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(article_email_frequency=ArticleEmailFrequency.WEEKLY)
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)
        self.handler.create_notifications_for_article(article.id)

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_digest_email"
        ) as send_email:
            self.handler.send_article_digest("weekly")

        send_email.assert_called_once()

    def test_digest_skips_already_read_rows(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(article_email_frequency=ArticleEmailFrequency.HOURLY)
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)
        self.handler.create_notifications_for_article(article.id)
        self.handler.mark_article_read_for_user(follower.id, article.id)

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_digest_email"
        ) as send_email:
            self.handler.send_article_digest("hourly")

        send_email.assert_not_called()

    def test_digest_skips_never_cadence(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(article_email_frequency=ArticleEmailFrequency.NEVER)
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)
        self.handler.create_notifications_for_article(article.id)

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_digest_email"
        ) as send_email:
            self.handler.send_article_digest("hourly")
            self.handler.send_article_digest("never")

        send_email.assert_not_called()


@pytest.mark.django_db
class TestHouseChannelLogging:
    def setup_method(self):
        self.handler = DjangoNotificationHandler()

    def test_logs_for_house_channel_article(self, caplog):
        from tests.factories import ensure_house_project  # noqa: PLC0415

        house = ensure_house_project()
        channel = ChannelFactory(project=house, name="Competition Winners")
        follower = UserFactory(article_email_frequency=ArticleEmailFrequency.HOURLY)
        _follow_channel(follower, house, channel)
        article = PublishedArticleFactory(project=house, channel=channel)

        with caplog.at_level(logging.INFO):
            self.handler.create_notifications_for_article(article.id)

        relevant = [
            r
            for r in caplog.records
            if "house_channel_article_enqueued" in r.getMessage()
        ]
        assert len(relevant) >= 1
        assert str(follower.id) in relevant[0].getMessage()

    def test_logs_for_never_cadence_too(self, caplog):
        from tests.factories import ensure_house_project  # noqa: PLC0415

        house = ensure_house_project()
        channel = ChannelFactory(project=house, name="Product Updates")
        follower = UserFactory(article_email_frequency=ArticleEmailFrequency.NEVER)
        _follow_channel(follower, house, channel)
        article = PublishedArticleFactory(project=house, channel=channel)

        with caplog.at_level(logging.INFO):
            self.handler.create_notifications_for_article(article.id)

        msg = "\n".join(
            r.getMessage() for r in caplog.records if "house_channel" in r.getMessage()
        )
        assert "recipient_frequency=never" in msg

    def test_no_log_for_non_house_channel_article(self, caplog):
        project = ProjectFactory()  # not house
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        _follow_channel(follower, project, channel)
        article = PublishedArticleFactory(project=project, channel=channel)

        with caplog.at_level(logging.INFO):
            self.handler.create_notifications_for_article(article.id)

        assert not any(
            "house_channel_article_enqueued" in r.getMessage() for r in caplog.records
        )


@pytest.mark.django_db
class TestPublishHandlerIntegration:
    def setup_method(self):
        self.article_handler = DjangoArticleHandler()
        self.notif_handler = DjangoNotificationHandler()

    def test_live_publish_creates_in_app_row(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        _follow_channel(follower, project, channel)

        article = self.article_handler.create_draft(
            project_id=project.id,
            channel_id=channel.id,
            author_id=project.creator.id,
            title="Hi",
            body="There",
        )
        self.article_handler.publish(article.id)

        assert Notification.objects.filter(
            recipient=follower, article_id=article.id
        ).exists()

    def test_backdated_publish_via_handler_creates_no_rows(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        _follow_channel(follower, project, channel)

        article = self.article_handler.create_draft(
            project_id=project.id,
            channel_id=channel.id,
            author_id=project.creator.id,
            title="Hi",
            body="There",
        )

        self.article_handler.publish(
            article.id, published_at=timezone.now() - timedelta(days=7)
        )

        assert not Notification.objects.filter(article_id=article.id).exists()
