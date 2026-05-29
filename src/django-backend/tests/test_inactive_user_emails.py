from unittest.mock import patch

import pytest
from hamcrest import assert_that, equal_to

from apps.notifications.models import Notification, NotificationCadence
from apps.projects.models import ProjectStatus
from services.email.django_impl.query import DjangoEmailQuery
from services.notifications.django_impl.handler import DjangoNotificationHandler
from tests.factories import (
    BroadcastEmailFactory,
    DiscussionFactory,
    NotificationFactory,
    ProjectFactory,
    UserFactory,
    make_broadcast_follower,
)

_SEND_EMAIL = (
    "services.email.django_impl.handler"
    ".DjangoEmailHandler"
    ".send_discussion_notification_email"
)

_IMMEDIATE = NotificationCadence.IMMEDIATE


@pytest.mark.django_db
class TestBroadcastExcludesInactiveUsers:
    def test_platform_update_excludes_inactive_users(self):
        active = make_broadcast_follower("platform_updates")
        inactive = make_broadcast_follower("platform_updates", is_active=False)

        broadcast = BroadcastEmailFactory(
            email_type="platform_updates",
            created_by=UserFactory(is_staff=True, is_superuser=True),
        )
        recipients = DjangoEmailQuery().resolve_broadcast_recipients(broadcast)
        recipient_ids = set(recipients.values_list("id", flat=True))

        assert_that(active.id in recipient_ids, equal_to(True))
        assert_that(inactive.id in recipient_ids, equal_to(False))

    def test_competition_results_excludes_inactive_users(self):
        active = make_broadcast_follower("competition_results")
        inactive = make_broadcast_follower("competition_results", is_active=False)

        broadcast = BroadcastEmailFactory(
            email_type="competition_results",
            created_by=UserFactory(is_staff=True, is_superuser=True),
        )
        recipients = DjangoEmailQuery().resolve_broadcast_recipients(broadcast)
        recipient_ids = set(recipients.values_list("id", flat=True))

        assert_that(active.id in recipient_ids, equal_to(True))
        assert_that(inactive.id in recipient_ids, equal_to(False))

    def test_individual_recipients_excludes_inactive_users(self):
        active = UserFactory()
        inactive = UserFactory(is_active=False)

        broadcast = BroadcastEmailFactory(
            individual_recipients=[active, inactive],
        )
        recipients = DjangoEmailQuery().resolve_broadcast_recipients(broadcast)

        assert_that(list(recipients), equal_to([active]))


@pytest.mark.django_db
class TestDiscussionNotificationsExcludeInactiveUsers:
    @pytest.fixture
    def handler(self):
        return DjangoNotificationHandler()

    def test_reply_does_not_notify_inactive_project_owner(self, handler):
        inactive_owner = UserFactory(is_active=False, notification_frequency=_IMMEDIATE)
        project = ProjectFactory(owner=inactive_owner, status=ProjectStatus.APPROVED)
        author = UserFactory()
        discussion = DiscussionFactory(project=project, author=author)

        handler.create_notifications_for_discussion(discussion.id)

        assert_that(Notification.objects.count(), equal_to(0))

    def test_reply_does_not_notify_inactive_thread_participant(self, handler):
        owner = UserFactory(notification_frequency=_IMMEDIATE)
        project = ProjectFactory(owner=owner, status=ProjectStatus.APPROVED)
        root_author = UserFactory(notification_frequency=_IMMEDIATE)
        root = DiscussionFactory(project=project, author=root_author)
        inactive_participant = UserFactory(
            is_active=False, notification_frequency=_IMMEDIATE
        )
        DiscussionFactory(project=project, author=inactive_participant, parent=root)
        replier = UserFactory()
        reply = DiscussionFactory(project=project, author=replier, parent=root)

        with patch(_SEND_EMAIL):
            handler.create_notifications_for_discussion(reply.id)

        recipient_ids = set(Notification.objects.values_list("recipient_id", flat=True))
        assert_that(inactive_participant.id not in recipient_ids, equal_to(True))
        assert_that(owner.id in recipient_ids, equal_to(True))
        assert_that(root_author.id in recipient_ids, equal_to(True))

    def test_batch_digest_skips_inactive_users(self, handler):
        inactive = UserFactory(is_active=False)
        active = UserFactory()
        project = ProjectFactory(status=ProjectStatus.APPROVED)

        # Manually create notifications for both (simulating pre-existing records)
        discussion = DiscussionFactory(project=project, author=UserFactory())
        NotificationFactory(
            recipient=inactive,
            discussion=discussion,
            email_cadence=NotificationCadence.HOURLY,
        )
        NotificationFactory(
            recipient=active,
            discussion=discussion,
            email_cadence=NotificationCadence.HOURLY,
        )

        with patch(
            "services.email.django_impl.handler"
            ".DjangoEmailHandler"
            ".send_discussion_digest_email"
        ) as mock_digest:
            handler.send_batch_notifications(NotificationCadence.HOURLY)

        # Only called once — for the active user
        assert_that(mock_digest.call_count, equal_to(1))
        sent_notifications = mock_digest.call_args[1]["notifications"]
        assert_that(sent_notifications[0].recipient_id, equal_to(active.id))
