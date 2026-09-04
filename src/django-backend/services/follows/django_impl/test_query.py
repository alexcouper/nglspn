from collections.abc import Callable

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.follows.models import Channel, Follow, FollowedChannel
from services.follows.django_impl.query import DjangoFollowQuery
from services.follows.query_interface import FollowState
from tests.factories import (
    ArticleFactory,
    ProjectFactory,
    ProjectImageFactory,
    UserFactory,
    article_image,
)


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
        # A channel that does not exist yet is created after the Follow, so
        # the channel post_save receiver has already enrolled the user in it.
        channel, _ = Channel.objects.get_or_create(project=project, name=name)
        FollowedChannel.objects.get_or_create(follow=follow, channel=channel)
    return follow


def _follow_projects_with_a_hero(user, count):
    for _ in range(count):
        project = ProjectFactory()
        ProjectImageFactory(project=project, is_hero=True)
        _make_follow(user, project, ["Updates", "Releases"])


def _count_queries(work: Callable[[], object]) -> int:
    with CaptureQueriesContext(connection) as queries:
        work()
    return len(queries)


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
class TestListUserFollowsQueryCount:
    def setup_method(self):
        self.query = DjangoFollowQuery()

    def test_does_not_query_per_followed_project(self):
        user = UserFactory()
        _follow_projects_with_a_hero(user, count=1)
        one_follow = _count_queries(lambda: self.query.list_user_follows(user.id))

        _follow_projects_with_a_hero(user, count=3)
        four_follows = _count_queries(lambda: self.query.list_user_follows(user.id))

        assert four_follows == one_follow


@pytest.mark.django_db
class TestListUserFollowsHeroImage:
    def setup_method(self):
        self.query = DjangoFollowQuery()

    def test_uses_the_projects_hero_image(self):
        user = UserFactory()
        project = ProjectFactory()
        hero = ProjectImageFactory(project=project, is_hero=True)
        _make_follow(user, project, ["Updates"])

        (item,) = self.query.list_user_follows(user.id)

        assert item.project_hero_image_url == hero.url

    def test_ignores_images_uploaded_for_an_article(self):
        user = UserFactory()
        project = ProjectFactory()
        article_image(ArticleFactory(project=project))
        _make_follow(user, project, ["Updates"])

        (item,) = self.query.list_user_follows(user.id)

        assert item.project_hero_image_url is None

    def test_ignores_an_upload_that_never_completed(self):
        user = UserFactory()
        project = ProjectFactory()
        ProjectImageFactory(project=project, is_hero=True, upload_status="pending")
        _make_follow(user, project, ["Updates"])

        (item,) = self.query.list_user_follows(user.id)

        assert item.project_hero_image_url is None


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
