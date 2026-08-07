from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.notifications.models import Notification, NotificationCadence
from tests.factories import (
    ArticleFactory,
    DiscussionFactory,
    NotificationFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestTargetXorGuard:
    """The XOR `(discussion IS NULL) != (article IS NULL)` is enforced at the
    DB CHECK on Postgres and via `Notification.save()` on SQLite.
    """

    def test_both_discussion_and_article_raises(self):
        notification = Notification(
            recipient=UserFactory(),
            discussion=DiscussionFactory(),
            article=ArticleFactory(),
            email_cadence=NotificationCadence.IMMEDIATE,
        )

        with pytest.raises(ValidationError, match="exactly one"):
            notification.save()

    def test_neither_discussion_nor_article_raises(self):
        notification = Notification(
            recipient=UserFactory(),
            discussion=None,
            article=None,
            email_cadence=NotificationCadence.IMMEDIATE,
        )

        with pytest.raises(ValidationError, match="exactly one"):
            notification.save()

    def test_discussion_only_saves(self):
        notification = Notification(
            recipient=UserFactory(),
            discussion=DiscussionFactory(),
            email_cadence=NotificationCadence.IMMEDIATE,
        )

        notification.save()

        assert notification.pk is not None

    def test_article_only_saves(self):
        notification = Notification(
            recipient=UserFactory(),
            article=ArticleFactory(),
            email_cadence=NotificationCadence.IMMEDIATE,
        )

        notification.save()

        assert notification.pk is not None


@pytest.mark.django_db
class TestPartialUniqueConstraints:
    """One `(recipient, discussion)` and one `(recipient, article)` row each,
    independent of one another. Two partial unique constraints replaced the
    single pre-article `(recipient, discussion)` constraint.
    """

    def test_recipient_discussion_pair_is_unique(self):
        recipient = UserFactory()
        discussion = DiscussionFactory()
        NotificationFactory(recipient=recipient, discussion=discussion)

        dup = Notification(
            recipient=recipient,
            discussion=discussion,
            email_cadence=NotificationCadence.IMMEDIATE,
        )
        with pytest.raises(IntegrityError):
            dup.save()

    def test_recipient_article_pair_is_unique(self):
        recipient = UserFactory()
        article = ArticleFactory()
        Notification.objects.create(
            recipient=recipient,
            article=article,
            email_cadence=NotificationCadence.IMMEDIATE,
        )

        dup = Notification(
            recipient=recipient,
            article=article,
            email_cadence=NotificationCadence.IMMEDIATE,
        )
        with pytest.raises(IntegrityError):
            dup.save()

    def test_same_recipient_may_hold_both_a_discussion_and_an_article_row(self):
        recipient = UserFactory()

        NotificationFactory(recipient=recipient, discussion=DiscussionFactory())
        Notification.objects.create(
            recipient=recipient,
            article=ArticleFactory(),
            email_cadence=NotificationCadence.IMMEDIATE,
        )

        assert Notification.objects.filter(recipient=recipient).count() == 2

    def test_different_recipients_may_each_hold_a_row_for_the_same_article(self):
        article = ArticleFactory()
        u1 = UserFactory()
        u2 = UserFactory()
        Notification.objects.create(
            recipient=u1,
            article=article,
            email_cadence=NotificationCadence.IMMEDIATE,
        )
        Notification.objects.create(
            recipient=u2,
            article=article,
            email_cadence=NotificationCadence.IMMEDIATE,
        )

        assert Notification.objects.filter(article=article).count() == 2


# 5.5 (mixed digest rendering) is deferred — the recipient currently gets two
# digest emails when both kinds are pending. End-to-end tests live with the
# batch send path in services/notifications/django_impl/test_article_fanout.py.
