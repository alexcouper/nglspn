"""Following a person: the handler pair, the query and the Following list."""

from __future__ import annotations

import pytest

from apps.follows.models import PERSONAL_CHANNEL_NAME, Follow, FollowedChannel
from services.follows.django_impl.handler import DjangoFollowHandler
from services.follows.django_impl.query import DjangoFollowQuery
from services.follows.exceptions import SelfFollowError
from tests.factories import (
    ProjectFactory,
    UserFactory,
    give_avatar,
    personal_channel,
)


@pytest.fixture
def handler():
    return DjangoFollowHandler()


@pytest.fixture
def query():
    return DjangoFollowQuery()


def followed_channels_of(user) -> set:
    return set(
        FollowedChannel.objects.filter(follow__user=user).values_list(
            "channel_id", flat=True
        )
    )


@pytest.mark.django_db
class TestFollowUser:
    def test_follow_creates_the_row_and_reports_followed(self, handler, query):
        follower, person = UserFactory(), UserFactory()

        state = handler.follow_user(follower.id, person)

        assert state.is_followed is True
        assert query.is_following_user(follower.id, person.id) is True

    def test_follow_is_idempotent(self, handler):
        follower, person = UserFactory(), UserFactory()
        handler.follow_user(follower.id, person)

        handler.follow_user(follower.id, person)

        assert Follow.objects.filter(user=follower, followed_user=person).count() == 1

    def test_self_follow_raises_and_writes_nothing(self, handler):
        user = UserFactory()

        with pytest.raises(SelfFollowError):
            handler.follow_user(user.id, user)

        assert not Follow.objects.filter(user=user).exists()

    def test_following_a_person_with_a_channel_enrols_it(self, handler):
        follower, person = UserFactory(), UserFactory()
        channel = personal_channel(person)

        handler.follow_user(follower.id, person)

        assert followed_channels_of(follower) == {channel.id}

    def test_following_a_person_without_a_channel_enrols_nothing(self, handler):
        follower, person = UserFactory(), UserFactory()

        handler.follow_user(follower.id, person)

        assert followed_channels_of(follower) == set()

    def test_the_persons_later_channel_enrols_the_follower(self, handler):
        follower, person = UserFactory(), UserFactory()
        handler.follow_user(follower.id, person)

        channel = personal_channel(person)

        assert followed_channels_of(follower) == {channel.id}

    def test_unfollow_removes_follow_and_channel_rows(self, handler, query):
        follower, person = UserFactory(), UserFactory()
        personal_channel(person)
        handler.follow_user(follower.id, person)

        handler.unfollow_user(follower.id, person)

        assert query.is_following_user(follower.id, person.id) is False
        assert followed_channels_of(follower) == set()

    def test_unfollow_when_not_following_is_a_noop(self, handler):
        follower, person = UserFactory(), UserFactory()

        handler.unfollow_user(follower.id, person)

        assert not Follow.objects.filter(user=follower).exists()


@pytest.mark.django_db
class TestIsFollowingUser:
    def test_anonymous_is_never_following(self, query):
        assert query.is_following_user(None, UserFactory().id) is False

    def test_following_a_project_of_theirs_is_not_following_them(self, handler, query):
        follower, person = UserFactory(), UserFactory()
        handler.follow(follower.id, ProjectFactory(owner=person))

        assert query.is_following_user(follower.id, person.id) is False


@pytest.mark.django_db
class TestFollowsListCarriesBothKinds:
    def test_a_followed_person_is_listed_beside_a_project(self, handler, query):
        follower = UserFactory()
        person = UserFactory(first_name="Ada", last_name="Lovelace")
        give_avatar(person)
        project = ProjectFactory(slug="p", title="P")
        handler.follow(follower.id, project)
        handler.follow_user(follower.id, person)

        by_target = {item.target: item for item in query.list_user_follows(follower.id)}

        assert set(by_target) == {"project", "user"}
        user_entry = by_target["user"]
        assert user_entry.user_id == person.id
        assert user_entry.user_name == "Ada Lovelace"
        assert user_entry.user_avatar_url == person.avatar_url
        assert (user_entry.project_slug, user_entry.project_title) == (None, None)
        project_entry = by_target["project"]
        assert project_entry.project_slug == "p"
        assert (project_entry.user_id, project_entry.user_name) == (None, None)

    def test_a_followed_persons_channel_is_listed_with_its_state(self, handler, query):
        follower, person = UserFactory(), UserFactory()
        channel = personal_channel(person)
        handler.follow_user(follower.id, person)

        [entry] = query.list_user_follows(follower.id)

        [state] = entry.channels
        assert (state.channel_id, state.channel_name, state.followed) == (
            channel.id,
            PERSONAL_CHANNEL_NAME,
            True,
        )

    def test_a_followed_person_without_a_channel_has_an_empty_list(
        self, handler, query
    ):
        follower, person = UserFactory(), UserFactory()
        handler.follow_user(follower.id, person)

        [entry] = query.list_user_follows(follower.id)

        assert entry.channels == []
