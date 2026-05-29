"""Integration: follow + per-channel email preference drive the broadcast set.

The async-broadcast-send pipeline resolves recipients from Follow +
FollowChannelPreference on the house project's named channels. These tests
exercise the follow / unfollow / patch handlers together with that resolver.
"""

import pytest

from apps.follows.models import Channel
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

    def test_disabling_channel_email_excludes_from_competition_results(self):
        user = UserFactory()
        house, cw, _ = _seed_house_with_channels()
        self.handler.follow(user.id, house)

        recipients = self.user_query.list_opted_in_for_broadcast_type(
            "competition_results"
        )
        assert recipients.filter(pk=user.pk).exists()

        self.handler.set_channel_preference(
            user.id, "naglasupan", cw.id, email_enabled=False
        )

        recipients = self.user_query.list_opted_in_for_broadcast_type(
            "competition_results"
        )
        assert not recipients.filter(pk=user.pk).exists()

    def test_disabling_channel_email_excludes_from_platform_updates(self):
        user = UserFactory()
        house, _, pu = _seed_house_with_channels()
        self.handler.follow(user.id, house)

        self.handler.set_channel_preference(
            user.id, "naglasupan", pu.id, email_enabled=False
        )

        platform = self.user_query.list_opted_in_for_broadcast_type("platform_updates")
        assert not platform.filter(pk=user.pk).exists()
        # The other channel still includes them.
        competition = self.user_query.list_opted_in_for_broadcast_type(
            "competition_results"
        )
        assert competition.filter(pk=user.pk).exists()

    def test_unfollow_excludes_from_both_types(self):
        user = UserFactory()
        house, _, _ = _seed_house_with_channels()
        self.handler.follow(user.id, house)

        self.handler.unfollow(user.id, house)

        for email_type in ("competition_results", "platform_updates"):
            recipients = self.user_query.list_opted_in_for_broadcast_type(email_type)
            assert not recipients.filter(pk=user.pk).exists()
