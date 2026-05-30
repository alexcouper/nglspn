import pytest

from apps.follows.models import Follow, FollowedChannel
from apps.follows.services import anoint_house_project
from tests.factories import ProjectFactory, UserFactory

HOUSE_CHANNELS = {"Updates", "Competition Winners", "Product Updates"}


def _channel_names(project):
    return set(project.channels.values_list("name", flat=True))


def _prefs_by_channel(user, project):
    return {
        p.channel.name: p
        for p in FollowedChannel.objects.filter(
            follow__user=user, follow__project=project
        )
    }


@pytest.mark.django_db
class TestAnointHouseProject:
    def test_flags_project_and_demotes_previous_house(self):
        first = ProjectFactory()
        anoint_house_project(first)
        assert first.is_house_project is True

        second = ProjectFactory()
        anoint_house_project(second)

        first.refresh_from_db()
        second.refresh_from_db()
        assert second.is_house_project is True
        assert first.is_house_project is False

    def test_creates_the_named_broadcast_channels(self):
        project = ProjectFactory()

        anoint_house_project(project)

        assert _channel_names(project) >= HOUSE_CHANNELS

    def test_backfills_active_users_with_followed_channels(self):
        # Created before any house exists, so the auto-follow signal no-ops and
        # the backfill is the only thing that follows them.
        user = UserFactory()
        project = ProjectFactory()

        anoint_house_project(project)

        assert Follow.objects.filter(user=user, project=project).exists()
        prefs = _prefs_by_channel(user, project)
        assert set(prefs) == HOUSE_CHANNELS

    def test_skips_inactive_and_system_users(self):
        inactive = UserFactory(is_active=False)
        system = UserFactory(is_system_user=True)
        project = ProjectFactory()

        anoint_house_project(project)

        assert not Follow.objects.filter(user=inactive).exists()
        assert not Follow.objects.filter(user=system).exists()

    def test_is_idempotent(self):
        UserFactory()
        project = ProjectFactory()

        first = anoint_house_project(project)
        second = anoint_house_project(project)

        assert first["follows_created"] >= 1
        assert second["follows_created"] == 0
        assert _channel_names(project) >= HOUSE_CHANNELS
        # No duplicate preference rows.
        for follow in Follow.objects.filter(project=project):
            assert FollowedChannel.objects.filter(follow=follow).count() == len(
                HOUSE_CHANNELS
            )
