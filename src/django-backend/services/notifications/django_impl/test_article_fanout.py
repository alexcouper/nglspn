from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.follows.models import Follow, FollowChannelPreference
from apps.notifications.models import Notification, NotificationCadence
from services.articles.django_impl.handler import DjangoArticleHandler
from services.notifications.django_impl.handler import DjangoNotificationHandler
from tests.factories import (
    ArticleFactory,
    ChannelFactory,
    ProjectFactory,
    ProjectImageFactory,
    PublishedArticleFactory,
    UserFactory,
)


def _seed_follow(user, project, channel, *, email: bool, in_app: bool):
    """Set up `(user, project, channel)` follow with the given switches.

    A small helper rather than a factory because it composes two rows
    (Follow + FollowChannelPreference) with an `update_or_create` on the
    pair to be idempotent against the test setup. Keeping it as a helper
    keeps each call concise and avoids inventing factory plumbing for a
    relationship that only matters in these notification tests.
    """
    follow, _ = Follow.objects.get_or_create(user=user, project=project)
    FollowChannelPreference.objects.update_or_create(
        follow=follow,
        channel=channel,
        defaults={"email_enabled": email, "in_app_enabled": in_app},
    )
    return follow


@pytest.mark.django_db
class TestCreateNotificationsForArticle:
    def setup_method(self):
        self.handler = DjangoNotificationHandler()

    def test_in_app_on_email_on_creates_row_and_sends_immediate(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(notification_frequency=NotificationCadence.IMMEDIATE)
        _seed_follow(follower, project, channel, email=True, in_app=True)
        article = PublishedArticleFactory(project=project, channel=channel)

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_notification_email"
        ) as send_email:
            self.handler.create_notifications_for_article(article.id)

        send_email.assert_called_once()
        row = Notification.objects.get(recipient=follower, article=article)
        assert row.in_app_read_at is None
        assert row.email_sent is True
        assert row.email_sent_at is not None
        assert row.email_cadence == NotificationCadence.IMMEDIATE

    def test_in_app_on_email_off_creates_row_no_email(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(notification_frequency=NotificationCadence.IMMEDIATE)
        _seed_follow(follower, project, channel, email=False, in_app=True)
        article = PublishedArticleFactory(project=project, channel=channel)

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_notification_email"
        ) as send_email:
            self.handler.create_notifications_for_article(article.id)

        send_email.assert_not_called()
        row = Notification.objects.get(recipient=follower, article=article)
        assert row.in_app_read_at is None
        assert row.email_sent is False

    def test_in_app_off_email_on_creates_pre_read_row_and_sends(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(notification_frequency=NotificationCadence.IMMEDIATE)
        _seed_follow(follower, project, channel, email=True, in_app=False)
        article = PublishedArticleFactory(project=project, channel=channel)

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_notification_email"
        ) as send_email:
            self.handler.create_notifications_for_article(article.id)

        send_email.assert_called_once()
        row = Notification.objects.get(recipient=follower, article=article)
        # Pre-read so it never surfaces in-app.
        assert row.in_app_read_at is not None
        assert row.email_sent is True

    def test_both_off_creates_no_row(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        _seed_follow(follower, project, channel, email=False, in_app=False)
        article = PublishedArticleFactory(project=project, channel=channel)

        self.handler.create_notifications_for_article(article.id)

        assert not Notification.objects.filter(recipient=follower).exists()

    def test_author_excluded(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        author = project.creator
        _seed_follow(author, project, channel, email=True, in_app=True)
        article = PublishedArticleFactory(
            project=project, channel=channel, author=author
        )

        self.handler.create_notifications_for_article(article.id)

        assert not Notification.objects.filter(recipient=author).exists()

    def test_inactive_user_excluded(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(is_active=False)
        _seed_follow(follower, project, channel, email=True, in_app=True)
        article = PublishedArticleFactory(project=project, channel=channel)

        self.handler.create_notifications_for_article(article.id)

        assert not Notification.objects.filter(recipient=follower).exists()

    def test_never_cadence_creates_in_app_but_no_email(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(notification_frequency=NotificationCadence.NEVER)
        _seed_follow(follower, project, channel, email=True, in_app=True)
        article = PublishedArticleFactory(project=project, channel=channel)

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_notification_email"
        ) as send_email:
            self.handler.create_notifications_for_article(article.id)

        send_email.assert_not_called()
        row = Notification.objects.get(recipient=follower, article=article)
        assert row.email_cadence == NotificationCadence.NEVER
        assert row.email_sent is False
        assert row.in_app_read_at is None

    def test_hourly_cadence_creates_row_but_does_not_fire_immediate(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(notification_frequency=NotificationCadence.HOURLY)
        _seed_follow(follower, project, channel, email=True, in_app=True)
        article = PublishedArticleFactory(project=project, channel=channel)

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_notification_email"
        ) as send_email:
            self.handler.create_notifications_for_article(article.id)

        send_email.assert_not_called()
        row = Notification.objects.get(recipient=follower, article=article)
        assert row.email_cadence == NotificationCadence.HOURLY
        assert row.email_sent is False

    def test_idempotent_on_re_invoke(self):
        """Second invocation should not duplicate rows (partial unique constraint)."""
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(notification_frequency=NotificationCadence.HOURLY)
        _seed_follow(follower, project, channel, email=False, in_app=True)
        article = PublishedArticleFactory(project=project, channel=channel)

        self.handler.create_notifications_for_article(article.id)
        self.handler.create_notifications_for_article(article.id)

        assert (
            Notification.objects.filter(recipient=follower, article=article).count()
            == 1
        )

    def test_draft_article_is_no_op(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        _seed_follow(follower, project, channel, email=True, in_app=True)
        article = ArticleFactory(project=project, channel=channel)

        self.handler.create_notifications_for_article(article.id)

        assert not Notification.objects.filter(article=article).exists()

    def test_unknown_article_id_is_no_op(self):
        # Should log a warning but not raise.
        self.handler.create_notifications_for_article(uuid.uuid4())

    def test_backdate_gating_is_not_owned_here(self):
        """Per design: HANDLERS.articles.publish owns backdate gating.

        Calling create_notifications_for_article directly with a published
        article — regardless of how old published_at is — SHALL fan out.
        """
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(notification_frequency=NotificationCadence.HOURLY)
        _seed_follow(follower, project, channel, email=False, in_app=True)
        article = PublishedArticleFactory(project=project, channel=channel)
        # Manually backdate.
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
        _seed_follow(user_a, project, channel, email=False, in_app=True)
        _seed_follow(user_b, project, channel, email=False, in_app=True)
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
        _seed_follow(user, project, channel, email=False, in_app=True)
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
class TestArticleBatchSendPath:
    """The HOURLY/DAILY batch picks up article rows whose email is wanted."""

    def setup_method(self):
        self.handler = DjangoNotificationHandler()

    def test_batch_sends_email_for_hourly_article_row(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(notification_frequency=NotificationCadence.HOURLY)
        _seed_follow(follower, project, channel, email=True, in_app=True)
        article = PublishedArticleFactory(project=project, channel=channel)
        # Live publish fan-out creates the row but doesn't send (HOURLY).
        self.handler.create_notifications_for_article(article.id)
        row = Notification.objects.get(recipient=follower, article=article)
        assert row.email_sent is False

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_notification_email"
        ) as send_email:
            self.handler.send_batch_notifications(NotificationCadence.HOURLY)

        send_email.assert_called_once()
        row.refresh_from_db()
        assert row.email_sent is True

    def test_batch_skips_already_read_article_row(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(notification_frequency=NotificationCadence.HOURLY)
        _seed_follow(follower, project, channel, email=True, in_app=True)
        article = PublishedArticleFactory(project=project, channel=channel)
        self.handler.create_notifications_for_article(article.id)
        self.handler.mark_article_read_for_user(follower.id, article.id)

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler.send_article_notification_email"
        ) as send_email:
            self.handler.send_batch_notifications(NotificationCadence.HOURLY)

        send_email.assert_not_called()


@pytest.mark.django_db
class TestPublishHandlerIntegration:
    """End-to-end: publish through HANDLERS.articles fires fan-out correctly."""

    def setup_method(self):
        self.article_handler = DjangoArticleHandler()
        self.notif_handler = DjangoNotificationHandler()

    def test_live_publish_creates_in_app_row(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory(notification_frequency=NotificationCadence.HOURLY)
        _seed_follow(follower, project, channel, email=False, in_app=True)
        image = ProjectImageFactory(project=project)

        article = self.article_handler.create_draft(
            project_id=project.id,
            channel_id=channel.id,
            author_id=project.creator.id,
            title="Hi",
            body="There",
            hero_image_id=image.id,
        )
        self.article_handler.publish(article.id)

        assert Notification.objects.filter(
            recipient=follower, article_id=article.id
        ).exists()

    def test_backdated_publish_via_handler_creates_no_rows(self):
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        follower = UserFactory()
        _seed_follow(follower, project, channel, email=True, in_app=True)
        image = ProjectImageFactory(project=project)

        article = self.article_handler.create_draft(
            project_id=project.id,
            channel_id=channel.id,
            author_id=project.creator.id,
            title="Hi",
            body="There",
            hero_image_id=image.id,
        )

        self.article_handler.publish(
            article.id, published_at=timezone.now() - timedelta(days=7)
        )

        assert not Notification.objects.filter(article_id=article.id).exists()
