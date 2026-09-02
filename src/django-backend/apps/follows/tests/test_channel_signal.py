import pytest
from django.db.models.signals import post_save

from apps.follows.models import Channel, Follow, FollowedChannel
from services import HANDLERS
from tests.factories import ChannelFactory, ProjectFactory, UserFactory


def follow_project(user, project) -> Follow:
    """Follow `project` the way `POST /follow` does, and return the Follow."""
    HANDLERS.follows.follow(user.id, project)
    return Follow.objects.get(user=user, project=project)


def followed_by(channel: Channel) -> set[Follow]:
    return {fc.follow for fc in FollowedChannel.objects.filter(channel=channel)}


@pytest.mark.django_db
class TestDefaultChannelSignal:
    def test_new_project_gets_updates_channel(self):
        project = ProjectFactory()
        channels = list(Channel.objects.filter(project=project))
        assert len(channels) == 1
        assert channels[0].name == "Updates"

    def test_re_saving_project_does_not_duplicate_channel(self):
        project = ProjectFactory()
        project.title = "Renamed"
        project.save()
        assert Channel.objects.filter(project=project, name="Updates").count() == 1

    def test_str_returns_project_title_and_channel_name(self):
        project = ProjectFactory(title="Demo Project")
        channel = Channel.objects.get(project=project, name="Updates")
        assert str(channel) == "Demo Project: Updates"


@pytest.mark.django_db
class TestNewChannelEnrolsExistingFollowers:
    def test_new_channel_enrols_every_existing_follower(self):
        project = ProjectFactory()
        followers = [follow_project(UserFactory(), project) for _ in range(2)]

        channel = ChannelFactory(project=project, name="Releases")

        assert followed_by(channel) == set(followers)

    def test_follower_of_another_project_is_not_enrolled(self):
        project, other_project = ProjectFactory(), ProjectFactory()
        follower = follow_project(UserFactory(), project)
        follow_project(UserFactory(), other_project)

        channel = ChannelFactory(project=project, name="Releases")

        assert followed_by(channel) == {follower}

    def test_renaming_a_channel_enrols_nobody(self):
        project = ProjectFactory()
        follow = follow_project(UserFactory(), project)
        channel = ChannelFactory(project=project, name="Releases")
        FollowedChannel.objects.filter(follow=follow, channel=channel).delete()

        channel.name = "Release notes"
        channel.save(update_fields=["name"])

        assert followed_by(channel) == set()

    def test_a_projects_first_channel_enrols_nobody(self):
        project = ProjectFactory()

        default_channel = Channel.objects.get(project=project, name="Updates")
        assert followed_by(default_channel) == set()

    def test_enrolment_does_not_duplicate_an_existing_row(self):
        project = ProjectFactory()
        follow = follow_project(UserFactory(), project)
        channel = ChannelFactory(project=project, name="Releases")

        # Re-send rather than call the receiver directly: importing it here
        # would register it, hiding a missing `FollowsConfig.ready()` from
        # every other test in this file.
        post_save.send(sender=Channel, instance=channel, created=True)

        rows = FollowedChannel.objects.filter(follow=follow, channel=channel)
        assert rows.count() == 1

    def test_a_follow_with_no_channels_is_enrolled_like_any_other(self):
        project = ProjectFactory()
        follow = follow_project(UserFactory(), project)
        FollowedChannel.objects.filter(follow=follow).delete()

        channel = ChannelFactory(project=project, name="Releases")

        assert followed_by(channel) == {follow}
