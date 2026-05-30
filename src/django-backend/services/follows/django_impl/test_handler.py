import pytest

from apps.follows.models import Channel, Follow, FollowedChannel
from services.follows.django_impl.handler import DjangoFollowHandler
from services.follows.exceptions import (
    ChannelNotOnProjectError,
    NotFollowingError,
)
from services.project.exceptions import ProjectNotFoundError
from tests.factories import ProjectFactory, UserFactory


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

    def test_second_follow_is_idempotent_and_does_not_auto_enrol_new_channels(self):
        user = UserFactory()
        project = ProjectFactory()
        self.handler.follow(user.id, project)
        initial_ids = set(
            FollowedChannel.objects.filter(follow__user=user).values_list(
                "channel_id", flat=True
            )
        )

        # A new channel appears after the original follow.
        Channel.objects.create(project=project, name="Releases")

        self.handler.follow(user.id, project)

        # Still only the channels that existed when the user first followed.
        current_ids = set(
            FollowedChannel.objects.filter(follow__user=user).values_list(
                "channel_id", flat=True
            )
        )
        assert current_ids == initial_ids
        assert Follow.objects.filter(user=user, project=project).count() == 1

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

    def test_unfollow_channel_removes_row(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        self.handler.follow(user.id, project)
        channel = Channel.objects.get(project=project, name="Updates")

        self.handler.unfollow_channel(user.id, "p", channel.id)

        assert not FollowedChannel.objects.filter(
            follow__user=user, channel=channel
        ).exists()
        # Follow row stays — empty-children Follow is a valid state.
        assert Follow.objects.filter(user=user, project=project).exists()

    def test_unfollow_channel_is_idempotent(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        self.handler.follow(user.id, project)
        channel = Channel.objects.get(project=project, name="Updates")

        self.handler.unfollow_channel(user.id, "p", channel.id)
        # Already gone; no raise.
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
