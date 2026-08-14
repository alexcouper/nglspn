import pytest
from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from apps.discussions.admin import DiscussionAdmin
from apps.discussions.models import Discussion
from apps.feed.admin import FeedEventAdmin
from apps.feed.models import FeedEvent, FeedEventKind
from apps.projects.models import ProjectStatus
from services import REPO
from tests.factories import DiscussionFactory, ProjectFactory


class FakeRequest:
    """Admin actions only ever use message_user, which ignores the request."""

    def __init__(self):
        self._messages = []


def feed_admin() -> FeedEventAdmin:
    admin = FeedEventAdmin(FeedEvent, AdminSite())
    admin.message_user = lambda *args, **kwargs: None
    return admin


def discussion_admin() -> DiscussionAdmin:
    admin = DiscussionAdmin(Discussion, AdminSite())
    admin.message_user = lambda *args, **kwargs: None
    return admin


def approved_project(**kwargs):
    return ProjectFactory(
        status=ProjectStatus.APPROVED, approved_at=timezone.now(), **kwargs
    )


def rendered_ids() -> set:
    return {e.id for e in REPO.feed.page(limit=50)}


@pytest.mark.django_db
class TestPromotingDiscussions:
    def test_promoting_a_thread_puts_it_in_the_feed(self):
        thread = DiscussionFactory(project=approved_project())

        discussion_admin().promote_to_feed(
            FakeRequest(), Discussion.objects.filter(pk=thread.pk)
        )

        event = FeedEvent.objects.get(discussion=thread)
        assert event.kind == FeedEventKind.DISCUSSION_PROMOTED
        assert event.id in rendered_ids()

    def test_replies_cannot_be_promoted(self):
        thread = DiscussionFactory(project=approved_project())
        reply = DiscussionFactory(project=thread.project, parent=thread)

        discussion_admin().promote_to_feed(
            FakeRequest(), Discussion.objects.filter(pk=reply.pk)
        )

        assert not FeedEvent.objects.filter(discussion=reply).exists()

    def test_promoting_twice_does_not_duplicate(self):
        thread = DiscussionFactory(project=approved_project())
        queryset = Discussion.objects.filter(pk=thread.pk)

        discussion_admin().promote_to_feed(FakeRequest(), queryset)
        discussion_admin().promote_to_feed(FakeRequest(), queryset)

        assert FeedEvent.objects.filter(discussion=thread).count() == 1


@pytest.mark.django_db
class TestFeedEventActions:
    def test_retiring_removes_an_entry_from_the_feed(self):
        project = approved_project()
        event = FeedEvent.objects.get(project=project)

        feed_admin().retire_entries(
            FakeRequest(), FeedEvent.objects.filter(pk=event.pk)
        )

        assert event.id not in rendered_ids()

    def test_restoring_puts_it_back(self):
        project = approved_project()
        event = FeedEvent.objects.get(project=project)
        queryset = FeedEvent.objects.filter(pk=event.pk)
        feed_admin().retire_entries(FakeRequest(), queryset)

        feed_admin().restore_entries(FakeRequest(), queryset)

        assert event.id in rendered_ids()

    def test_pinning_a_second_entry_replaces_the_first(self):
        first = FeedEvent.objects.get(project=approved_project())
        second = FeedEvent.objects.get(project=approved_project())
        admin = feed_admin()

        admin.pin_as_lead(FakeRequest(), FeedEvent.objects.filter(pk=first.pk))
        admin.pin_as_lead(FakeRequest(), FeedEvent.objects.filter(pk=second.pk))

        assert list(
            FeedEvent.objects.filter(is_pinned=True).values_list("pk", flat=True)
        ) == [second.pk]

    def test_pinning_several_at_once_is_refused(self):
        first = FeedEvent.objects.get(project=approved_project())
        second = FeedEvent.objects.get(project=approved_project())

        feed_admin().pin_as_lead(
            FakeRequest(), FeedEvent.objects.filter(pk__in=[first.pk, second.pk])
        )

        assert not FeedEvent.objects.filter(is_pinned=True).exists()
