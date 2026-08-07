"""Integration: follow + per-channel follow drive the broadcast set.

The async-broadcast-send pipeline resolves recipients from Follow +
FollowedChannel on the house project's named channels. These tests
exercise the follow / unfollow / per-channel handlers together with that
resolver.
"""

import pytest

from apps.follows.models import Channel
from apps.users.models import ArticleEmailFrequency
from services.follows.django_impl.handler import DjangoFollowHandler
from services.users.django_impl.query import DjangoUserQuery
from tests.factories import ProjectFactory, UserFactory


def _seed_house_with_channels():
    house = ProjectFactory(slug="naglasupan", title="Naglasúpan", is_house_project=True)
    cw, _ = Channel.objects.get_or_create(project=house, name="Competition Winners")
    pu, _ = Channel.objects.get_or_create(project=house, name="Product Updates")
    return house, cw, pu


@pytest.mark.django_db
class TestBroadcastRecipientResolution:
    def setup_method(self):
        self.handler = DjangoFollowHandler()
        self.user_query = DjangoUserQuery()

    def test_unfollowing_a_channel_excludes_from_that_broadcast_type(self):
        user = UserFactory()
        house, cw, _ = _seed_house_with_channels()
        self.handler.follow(user.id, house)

        recipients = self.user_query.list_opted_in_for_broadcast_type(
            "competition_results"
        )
        assert recipients.filter(pk=user.pk).exists()

        self.handler.unfollow_channel(user.id, "naglasupan", cw.id)

        recipients = self.user_query.list_opted_in_for_broadcast_type(
            "competition_results"
        )
        assert not recipients.filter(pk=user.pk).exists()

    def test_unfollowing_one_channel_does_not_affect_the_other(self):
        user = UserFactory()
        house, _cw, pu = _seed_house_with_channels()
        self.handler.follow(user.id, house)

        self.handler.unfollow_channel(user.id, "naglasupan", pu.id)

        platform = self.user_query.list_opted_in_for_broadcast_type("platform_updates")
        assert not platform.filter(pk=user.pk).exists()
        competition = self.user_query.list_opted_in_for_broadcast_type(
            "competition_results"
        )
        assert competition.filter(pk=user.pk).exists()

    def test_unfollow_project_excludes_from_both_types(self):
        user = UserFactory()
        house, _, _ = _seed_house_with_channels()
        self.handler.follow(user.id, house)

        self.handler.unfollow(user.id, house)

        for email_type in ("competition_results", "platform_updates"):
            recipients = self.user_query.list_opted_in_for_broadcast_type(email_type)
            assert not recipients.filter(pk=user.pk).exists()

    def test_article_email_frequency_never_excludes_user(self):
        user = UserFactory(article_email_frequency=ArticleEmailFrequency.NEVER)
        house, _, _ = _seed_house_with_channels()
        self.handler.follow(user.id, house)

        recipients = self.user_query.list_opted_in_for_broadcast_type(
            "platform_updates"
        )
        assert not recipients.filter(pk=user.pk).exists()
