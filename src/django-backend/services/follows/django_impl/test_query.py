import pytest

from apps.follows.models import Channel, Follow, FollowChannelPreference
from services.follows.django_impl.query import DjangoFollowQuery
from services.follows.query_interface import FollowState
from tests.factories import ProjectFactory, UserFactory


@pytest.mark.django_db
class TestDjangoFollowQuery:
    def setup_method(self):
        self.query = DjangoFollowQuery()

    def test_anonymous_is_not_followed(self):
        project = ProjectFactory()
        assert self.query.is_followed(None, project) is False
        assert self.query.get_state(None, project) == FollowState(is_followed=False)

    def test_unfollowed_user(self):
        user = UserFactory()
        project = ProjectFactory()
        assert self.query.is_followed(user.id, project) is False

    def test_followed_user(self):
        user = UserFactory()
        project = ProjectFactory()
        follow = Follow.objects.create(user=user, project=project)
        state = self.query.get_state(user.id, project)
        assert state.is_followed is True
        assert state.created_at == follow.created_at


def _make_follow(user, project, channel_names):
    follow = Follow.objects.create(user=user, project=project)
    for name in channel_names:
        channel, _ = Channel.objects.get_or_create(project=project, name=name)
        FollowChannelPreference.objects.create(
            follow=follow,
            channel=channel,
            email_enabled=True,
            in_app_enabled=True,
        )
    return follow


@pytest.mark.django_db
class TestListUserFollows:
    def setup_method(self):
        self.query = DjangoFollowQuery()

    def test_empty(self):
        user = UserFactory()
        assert self.query.list_user_follows(user.id) == []

    def test_one_follow(self):
        user = UserFactory()
        project = ProjectFactory(slug="solo", title="Solo")
        _make_follow(user, project, ["Updates"])

        result = self.query.list_user_follows(user.id)

        assert len(result) == 1
        item = result[0]
        assert item.project_slug == "solo"
        assert item.project_title == "Solo"
        assert {c.channel_name for c in item.channels} == {"Updates"}

    def test_many_follows_ordered_newest_first(self):
        user = UserFactory()
        a = ProjectFactory(slug="a", title="A")
        b = ProjectFactory(slug="b", title="B")
        _make_follow(user, a, ["Updates"])
        _make_follow(user, b, ["Updates"])

        result = self.query.list_user_follows(user.id)

        slugs = [r.project_slug for r in result]
        assert slugs == ["b", "a"]


@pytest.mark.django_db
class TestGetFollowPreferences:
    def setup_method(self):
        self.query = DjangoFollowQuery()

    def test_returns_none_when_not_following(self):
        user = UserFactory()
        ProjectFactory(slug="absent")
        assert self.query.get_follow_preferences(user.id, "absent") is None

    def test_returns_channels_when_following(self):
        user = UserFactory()
        project = ProjectFactory(slug="present", title="Present")
        _make_follow(user, project, ["Updates", "Releases"])

        result = self.query.get_follow_preferences(user.id, "present")

        assert result is not None
        assert result.project_slug == "present"
        names = {c.channel_name for c in result.channels}
        assert names == {"Updates", "Releases"}
