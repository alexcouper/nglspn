import pytest

from apps.follows.models import Channel, Follow, FollowedChannel
from services.follows.django_impl.handler import DjangoFollowHandler
from services.follows.exceptions import (
    ChannelNotOnProjectError,
    NotFollowingError,
)
from services.project.exceptions import ProjectNotFoundError
from tests.factories import ProjectFactory, UserFactory


def followed_channel_names(user) -> set[str]:
    return set(
        FollowedChannel.objects.filter(follow__user=user).values_list(
            "channel__name", flat=True
        )
    )


@pytest.mark.django_db
class TestFollow:
    def setup_method(self):
        self.handler = DjangoFollowHandler()

    def test_first_follow_enrols_every_current_channel(self):
        user = UserFactory()
        project = ProjectFactory()
        # Project factory's post_save signal already made "Updates"; add one more.
        Channel.objects.create(project=project, name="Releases")

        state = self.handler.follow(user.id, project)

        assert state.is_followed is True
        assert Follow.objects.filter(user=user, project=project).exists()
        assert FollowedChannel.objects.filter(follow__user=user).count() == 2

    def test_second_follow_does_not_re_enrol_an_unfollowed_channel(self):
        user = UserFactory()
        project = ProjectFactory()
        releases = Channel.objects.create(project=project, name="Releases")
        self.handler.follow(user.id, project)
        FollowedChannel.objects.filter(follow__user=user, channel=releases).delete()

        self.handler.follow(user.id, project)

        # Re-following is not a repair tool: an unticked channel stays unticked.
        assert not FollowedChannel.objects.filter(
            follow__user=user, channel=releases
        ).exists()
        assert Follow.objects.filter(user=user, project=project).count() == 1

    def test_a_channel_added_after_the_follow_enrols_the_follower(self):
        user = UserFactory()
        project = ProjectFactory()
        self.handler.follow(user.id, project)

        releases = Channel.objects.create(project=project, name="Releases")

        assert FollowedChannel.objects.filter(
            follow__user=user, channel=releases
        ).exists()

    def test_unfollow_hard_deletes_follow_and_followed_channels(self):
        user = UserFactory()
        project = ProjectFactory()
        self.handler.follow(user.id, project)
        assert Follow.objects.filter(user=user).exists()

        self.handler.unfollow(user.id, project)

        assert not Follow.objects.filter(user=user).exists()
        assert not FollowedChannel.objects.filter(follow__user=user).exists()

    def test_unfollow_when_not_following_is_noop(self):
        user = UserFactory()
        project = ProjectFactory()
        self.handler.unfollow(user.id, project)
        assert not Follow.objects.filter(user=user).exists()

    def test_re_follow_after_unfollow_enrols_every_current_channel(self):
        user = UserFactory()
        project = ProjectFactory()
        Channel.objects.create(project=project, name="Releases")

        self.handler.follow(user.id, project)
        self.handler.unfollow(user.id, project)
        self.handler.follow(user.id, project)

        assert FollowedChannel.objects.filter(follow__user=user).count() == 2


@pytest.mark.django_db
class TestFollowChannel:
    def setup_method(self):
        self.handler = DjangoFollowHandler()

    def test_follow_channel_adds_row_when_missing(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        self.handler.follow(user.id, project)
        # Pretend the user un-followed the channel earlier.
        channel = Channel.objects.get(project=project, name="Updates")
        FollowedChannel.objects.filter(follow__user=user, channel=channel).delete()

        state = self.handler.follow_channel(user.id, "p", channel.id)

        assert state.followed is True
        assert FollowedChannel.objects.filter(
            follow__user=user, channel=channel
        ).exists()

    def test_follow_channel_is_idempotent(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        self.handler.follow(user.id, project)
        channel = Channel.objects.get(project=project, name="Updates")

        self.handler.follow_channel(user.id, "p", channel.id)
        self.handler.follow_channel(user.id, "p", channel.id)

        assert (
            FollowedChannel.objects.filter(follow__user=user, channel=channel).count()
            == 1
        )

    def test_unfollow_channel_removes_row_and_keeps_follow(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        Channel.objects.create(project=project, name="Releases")
        self.handler.follow(user.id, project)
        channel = Channel.objects.get(project=project, name="Updates")

        state = self.handler.unfollow_channel(user.id, "p", channel.id)

        assert state.is_followed is True
        assert followed_channel_names(user) == {"Releases"}
        assert Follow.objects.filter(user=user, project=project).exists()

    def test_unfollow_channel_is_idempotent_while_others_remain(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        Channel.objects.create(project=project, name="Releases")
        self.handler.follow(user.id, project)
        channel = Channel.objects.get(project=project, name="Updates")

        self.handler.unfollow_channel(user.id, "p", channel.id)
        # Already gone; no raise.
        self.handler.unfollow_channel(user.id, "p", channel.id)

        assert followed_channel_names(user) == {"Releases"}

    def test_unfollow_last_channel_unfollows_the_project(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        self.handler.follow(user.id, project)
        channel = Channel.objects.get(project=project, name="Updates")

        state = self.handler.unfollow_channel(user.id, "p", channel.id)

        assert state.is_followed is False
        assert state.created_at is None
        assert not Follow.objects.filter(user=user, project=project).exists()
        assert not FollowedChannel.objects.filter(follow__user=user).exists()

    def test_unfollow_every_channel_in_turn_unfollows_the_project(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        Channel.objects.create(project=project, name="Releases")
        self.handler.follow(user.id, project)
        channels = list(Channel.objects.filter(project=project))

        states = [
            self.handler.unfollow_channel(user.id, "p", channel.id)
            for channel in channels
        ]

        assert [s.is_followed for s in states] == [True, False]
        assert not Follow.objects.filter(user=user, project=project).exists()

    def test_unfollow_channel_after_last_one_raises_not_following(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        self.handler.follow(user.id, project)
        channel = Channel.objects.get(project=project, name="Updates")
        self.handler.unfollow_channel(user.id, "p", channel.id)

        # The Follow went with it, so there is nothing left to unfollow from.
        with pytest.raises(NotFollowingError):
            self.handler.unfollow_channel(user.id, "p", channel.id)

    def test_follow_channel_unknown_project_raises(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        channel = Channel.objects.get(project=project, name="Updates")
        self.handler.follow(user.id, project)

        with pytest.raises(ProjectNotFoundError):
            self.handler.follow_channel(user.id, "ghost", channel.id)

    def test_follow_channel_wrong_project_raises(self):
        user = UserFactory()
        p = ProjectFactory(slug="p")
        other = ProjectFactory(slug="other")
        self.handler.follow(user.id, p)
        wrong_channel = Channel.objects.get(project=other, name="Updates")

        with pytest.raises(ChannelNotOnProjectError):
            self.handler.follow_channel(user.id, "p", wrong_channel.id)

    def test_follow_channel_when_not_following_project_raises(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        channel = Channel.objects.get(project=project, name="Updates")

        with pytest.raises(NotFollowingError):
            self.handler.follow_channel(user.id, "p", channel.id)
