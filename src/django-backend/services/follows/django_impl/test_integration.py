"""Cross-system invariant tests.

These assert that the Phase 2 PATCH and DELETE handlers keep the legacy email
broadcast pipeline in agreement: the pipeline reads ``email_opt_in_*`` flags;
the new handlers mirror writes to those flags for the house project's two
named channels, and clear both flags when the user unfollows the house
project.
"""

import pytest

from apps.follows.models import Channel
from services.follows.django_impl.handler import DjangoFollowHandler
from services.users.django_impl.query import DjangoUserQuery
from tests.factories import ProjectFactory, UserFactory


def _seed_house_with_channels():
    house = ProjectFactory(
        slug="naglasupan", title="Naglasúpan", is_house_project=True
    )
    cw, _ = Channel.objects.get_or_create(project=house, name="Competition Winners")
    pu, _ = Channel.objects.get_or_create(project=house, name="Product Updates")
    return house, cw, pu


@pytest.mark.django_db
class TestCrossSystemMirror:
    def setup_method(self):
        self.handler = DjangoFollowHandler()
        self.user_query = DjangoUserQuery()

    def test_patch_off_excludes_user_from_competition_results(self):
        user = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        house, cw, _ = _seed_house_with_channels()
        self.handler.follow(user.id, house)

        # Before: user is in the recipient set.
        recipients = self.user_query.list_opted_in_for_broadcast_type(
            "competition_results"
        )
        assert recipients.filter(pk=user.pk).exists()

        # Toggle off via PATCH.
        self.handler.set_channel_preference(
            user.id, "naglasupan", cw.id, email_enabled=False
        )

        # After: user is excluded.
        recipients = self.user_query.list_opted_in_for_broadcast_type(
            "competition_results"
        )
        assert not recipients.filter(pk=user.pk).exists()

    def test_patch_off_excludes_user_from_platform_updates(self):
        user = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        house, _, pu = _seed_house_with_channels()
        self.handler.follow(user.id, house)

        self.handler.set_channel_preference(
            user.id, "naglasupan", pu.id, email_enabled=False
        )

        recipients = self.user_query.list_opted_in_for_broadcast_type(
            "platform_updates"
        )
        assert not recipients.filter(pk=user.pk).exists()
        # Other broadcast type still includes them.
        other = self.user_query.list_opted_in_for_broadcast_type(
            "competition_results"
        )
        assert other.filter(pk=user.pk).exists()

    def test_unfollow_house_excludes_user_from_both_types(self):
        user = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        house, _, _ = _seed_house_with_channels()
        self.handler.follow(user.id, house)

        self.handler.unfollow(user.id, house)

        for email_type in ("competition_results", "platform_updates"):
            recipients = self.user_query.list_opted_in_for_broadcast_type(email_type)
            assert not recipients.filter(pk=user.pk).exists()
