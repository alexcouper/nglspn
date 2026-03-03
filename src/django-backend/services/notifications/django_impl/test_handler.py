from unittest.mock import patch

import pytest
from hamcrest import assert_that, equal_to

from apps.notifications.models import Notification, NotificationCadence
from apps.projects.models import ProjectStatus
from services.notifications.django_impl.handler import DjangoNotificationHandler
from tests.factories import DiscussionFactory, ProjectFactory, UserFactory

_SEND_EMAIL = (
    "services.email.django_impl.handler"
    ".DjangoEmailHandler"
    ".send_discussion_notification_email"
)


@pytest.fixture
def handler():
    return DjangoNotificationHandler()


@pytest.mark.django_db
class TestRecipientDetermination:
    def test_root_discussion_notifies_project_owner(self, handler) -> None:
        owner = UserFactory()
        project = ProjectFactory(owner=owner, status=ProjectStatus.APPROVED)
        author = UserFactory()
        discussion = DiscussionFactory(project=project, author=author)

        with patch(_SEND_EMAIL):
            handler.create_notifications_for_discussion(discussion.id)

        notifications = Notification.objects.all()
        assert_that(notifications.count(), equal_to(1))
        assert_that(notifications[0].recipient_id, equal_to(owner.id))

    def test_root_discussion_by_owner_creates_no_notifications(self, handler) -> None:
        owner = UserFactory()
        project = ProjectFactory(owner=owner, status=ProjectStatus.APPROVED)
        discussion = DiscussionFactory(project=project, author=owner)

        handler.create_notifications_for_discussion(discussion.id)

        assert_that(Notification.objects.count(), equal_to(0))

    def test_reply_notifies_project_owner_and_discussion_creator(self, handler) -> None:
        owner = UserFactory()
        project = ProjectFactory(owner=owner, status=ProjectStatus.APPROVED)
        discussion_author = UserFactory()
        root = DiscussionFactory(project=project, author=discussion_author)
        replier = UserFactory()
        reply = DiscussionFactory(project=project, author=replier, parent=root)

        with patch(_SEND_EMAIL):
            handler.create_notifications_for_discussion(reply.id)

        recipient_ids = set(Notification.objects.values_list("recipient_id", flat=True))
        assert_that(recipient_ids, equal_to({owner.id, discussion_author.id}))

    def test_reply_notifies_previous_participants(self, handler) -> None:
        owner = UserFactory()
        project = ProjectFactory(owner=owner, status=ProjectStatus.APPROVED)
        root_author = UserFactory()
        root = DiscussionFactory(project=project, author=root_author)
        participant_a = UserFactory()
        DiscussionFactory(project=project, author=participant_a, parent=root)
        participant_b = UserFactory()
        DiscussionFactory(project=project, author=participant_b, parent=root)
        new_replier = UserFactory()
        reply = DiscussionFactory(project=project, author=new_replier, parent=root)

        with patch(_SEND_EMAIL):
            handler.create_notifications_for_discussion(reply.id)

        recipient_ids = set(Notification.objects.values_list("recipient_id", flat=True))
        expected = {owner.id, root_author.id, participant_a.id, participant_b.id}
        assert_that(recipient_ids, equal_to(expected))

    def test_deduplication_when_owner_is_also_discussion_creator(self, handler) -> None:
        owner = UserFactory()
        project = ProjectFactory(owner=owner, status=ProjectStatus.APPROVED)
        root = DiscussionFactory(project=project, author=owner)
        replier = UserFactory()
        reply = DiscussionFactory(project=project, author=replier, parent=root)

        with patch(_SEND_EMAIL):
            handler.create_notifications_for_discussion(reply.id)

        owner_notifications = Notification.objects.filter(recipient=owner)
        assert_that(owner_notifications.count(), equal_to(1))

    def test_excludes_comment_author_from_notifications(self, handler) -> None:
        owner = UserFactory()
        project = ProjectFactory(owner=owner, status=ProjectStatus.APPROVED)
        author = UserFactory()
        discussion = DiscussionFactory(project=project, author=author)

        with patch(_SEND_EMAIL):
            handler.create_notifications_for_discussion(discussion.id)

        author_notifications = Notification.objects.filter(recipient=author)
        assert_that(author_notifications.count(), equal_to(0))

    def test_skips_users_with_never_cadence(self, handler) -> None:
        owner = UserFactory(notification_frequency=NotificationCadence.NEVER)
        project = ProjectFactory(owner=owner, status=ProjectStatus.APPROVED)
        author = UserFactory()
        discussion = DiscussionFactory(project=project, author=author)

        handler.create_notifications_for_discussion(discussion.id)

        assert_that(Notification.objects.count(), equal_to(0))

    def test_snapshots_user_cadence_at_creation_time(self, handler) -> None:
        owner = UserFactory(notification_frequency=NotificationCadence.HOURLY)
        project = ProjectFactory(owner=owner, status=ProjectStatus.APPROVED)
        author = UserFactory()
        discussion = DiscussionFactory(project=project, author=author)

        handler.create_notifications_for_discussion(discussion.id)

        notification = Notification.objects.get(recipient=owner)
        assert_that(notification.cadence, equal_to(NotificationCadence.HOURLY))
