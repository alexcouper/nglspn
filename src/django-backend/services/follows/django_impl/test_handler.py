import pytest

from apps.follows.models import Channel, Follow, FollowChannelPreference
from apps.users.models import User
from services.follows.django_impl.handler import DjangoFollowHandler
from services.follows.exceptions import (
    ChannelNotOnProjectError,
    EmptyPatchError,
    NotFollowingError,
)
from services.project.exceptions import ProjectNotFoundError
from tests.factories import ProjectFactory, UserFactory


@pytest.mark.django_db
class TestDjangoFollowHandler:
    def setup_method(self):
        self.handler = DjangoFollowHandler()

    def test_follow_creates_follow_and_prefs(self):
        user = UserFactory()
        project = ProjectFactory()
        # Project factory's post_save signal already made "Updates"; add one more
        # so we can assert prefs are created for every channel.
        Channel.objects.create(project=project, name="Releases")

        state = self.handler.follow(user.id, project)

        assert state.is_followed is True
        assert Follow.objects.filter(user=user, project=project).exists()
        prefs = FollowChannelPreference.objects.filter(follow__user=user)
        assert prefs.count() == 2
        for pref in prefs:
            assert pref.email_enabled is True
            assert pref.in_app_enabled is True

    def test_follow_is_idempotent_and_preserves_prefs(self):
        user = UserFactory()
        project = ProjectFactory()

        self.handler.follow(user.id, project)
        # Mutate a preference, then re-follow — must not be reset.
        pref = FollowChannelPreference.objects.get(follow__user=user)
        pref.email_enabled = False
        pref.save()

        self.handler.follow(user.id, project)

        pref.refresh_from_db()
        assert pref.email_enabled is False
        assert Follow.objects.filter(user=user, project=project).count() == 1

    def test_unfollow_hard_deletes(self):
        user = UserFactory()
        project = ProjectFactory()
        self.handler.follow(user.id, project)
        assert Follow.objects.filter(user=user).exists()

        self.handler.unfollow(user.id, project)

        assert not Follow.objects.filter(user=user).exists()
        assert not FollowChannelPreference.objects.filter(follow__user=user).exists()

    def test_unfollow_when_not_following_is_noop(self):
        user = UserFactory()
        project = ProjectFactory()
        # Should not raise.
        self.handler.unfollow(user.id, project)
        assert not Follow.objects.filter(user=user).exists()

    def test_re_follow_after_unfollow_is_fresh(self):
        user = UserFactory()
        project = ProjectFactory()
        self.handler.follow(user.id, project)
        pref = FollowChannelPreference.objects.get(follow__user=user)
        pref.email_enabled = False
        pref.save()

        self.handler.unfollow(user.id, project)
        self.handler.follow(user.id, project)

        new_pref = FollowChannelPreference.objects.get(follow__user=user)
        assert new_pref.email_enabled is True


def _seed_house_project_with_channels():
    house = ProjectFactory(slug="naglasupan", title="Naglasúpan", is_house_project=True)
    cw, _ = Channel.objects.get_or_create(project=house, name="Competition Winners")
    pu, _ = Channel.objects.get_or_create(project=house, name="Product Updates")
    return house, cw, pu


@pytest.mark.django_db
class TestSetChannelPreference:
    def setup_method(self):
        self.handler = DjangoFollowHandler()

    def test_updates_email_and_returns_state(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        self.handler.follow(user.id, project)
        channel = Channel.objects.get(project=project, name="Updates")

        state = self.handler.set_channel_preference(
            user.id, "p", channel.id, email_enabled=False
        )

        assert state.email_enabled is False
        assert state.in_app_enabled is True
        pref = FollowChannelPreference.objects.get(follow__user=user, channel=channel)
        assert pref.email_enabled is False

    def test_updates_in_app_only(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        self.handler.follow(user.id, project)
        channel = Channel.objects.get(project=project, name="Updates")

        self.handler.set_channel_preference(
            user.id, "p", channel.id, in_app_enabled=False
        )

        pref = FollowChannelPreference.objects.get(follow__user=user, channel=channel)
        assert pref.in_app_enabled is False
        assert pref.email_enabled is True

    def test_empty_patch_raises(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        self.handler.follow(user.id, project)
        channel = Channel.objects.get(project=project, name="Updates")

        with pytest.raises(EmptyPatchError):
            self.handler.set_channel_preference(user.id, "p", channel.id)

    def test_unknown_project_raises(self):
        user = UserFactory()
        with pytest.raises(ProjectNotFoundError):
            self.handler.set_channel_preference(
                user.id,
                "ghost",
                Channel(name="x").id,  # arbitrary
                email_enabled=False,
            )

    def test_channel_not_on_project_raises(self):
        user = UserFactory()
        p = ProjectFactory(slug="p")
        other = ProjectFactory(slug="other")
        self.handler.follow(user.id, p)
        wrong_channel = Channel.objects.get(project=other, name="Updates")

        with pytest.raises(ChannelNotOnProjectError):
            self.handler.set_channel_preference(
                user.id, "p", wrong_channel.id, email_enabled=False
            )

    def test_not_following_raises(self):
        user = UserFactory()
        project = ProjectFactory(slug="p")
        channel = Channel.objects.get(project=project, name="Updates")

        with pytest.raises(NotFollowingError):
            self.handler.set_channel_preference(
                user.id, "p", channel.id, email_enabled=False
            )


@pytest.mark.django_db
class TestMirrorLegacyFlag:
    def setup_method(self):
        self.handler = DjangoFollowHandler()

    def test_mirror_fires_for_competition_winners(self):
        user = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        house, cw, _ = _seed_house_project_with_channels()
        self.handler.follow(user.id, house)

        self.handler.set_channel_preference(
            user.id, "naglasupan", cw.id, email_enabled=False
        )

        user.refresh_from_db()
        assert user.email_opt_in_competition_results is False
        assert user.email_opt_in_platform_updates is True

    def test_mirror_fires_for_product_updates(self):
        user = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        house, _, pu = _seed_house_project_with_channels()
        self.handler.follow(user.id, house)

        self.handler.set_channel_preference(
            user.id, "naglasupan", pu.id, email_enabled=False
        )

        user.refresh_from_db()
        assert user.email_opt_in_platform_updates is False
        assert user.email_opt_in_competition_results is True

    def test_mirror_does_not_fire_for_updates_channel(self):
        user = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        house, _, _ = _seed_house_project_with_channels()
        self.handler.follow(user.id, house)
        updates_channel = Channel.objects.get(project=house, name="Updates")

        self.handler.set_channel_preference(
            user.id, "naglasupan", updates_channel.id, email_enabled=False
        )

        user.refresh_from_db()
        assert user.email_opt_in_competition_results is True
        assert user.email_opt_in_platform_updates is True

    def test_mirror_does_not_fire_for_non_house_project(self):
        user = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        project = ProjectFactory(slug="p")
        cw = Channel.objects.create(project=project, name="Competition Winners")
        self.handler.follow(user.id, project)

        self.handler.set_channel_preference(user.id, "p", cw.id, email_enabled=False)

        user.refresh_from_db()
        assert user.email_opt_in_competition_results is True

    def test_mirror_does_not_fire_when_only_in_app(self):
        user = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        house, cw, _ = _seed_house_project_with_channels()
        self.handler.follow(user.id, house)

        self.handler.set_channel_preference(
            user.id, "naglasupan", cw.id, in_app_enabled=False
        )

        user.refresh_from_db()
        assert user.email_opt_in_competition_results is True


@pytest.mark.django_db
class TestUnfollowMirror:
    def setup_method(self):
        self.handler = DjangoFollowHandler()

    def test_unfollow_house_clears_legacy_flags(self):
        user = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        house, _, _ = _seed_house_project_with_channels()
        self.handler.follow(user.id, house)

        self.handler.unfollow(user.id, house)

        user.refresh_from_db()
        assert user.email_opt_in_competition_results is False
        assert user.email_opt_in_platform_updates is False

    def test_unfollow_non_house_does_not_touch_legacy_flags(self):
        user = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        project = ProjectFactory(slug="p")
        self.handler.follow(user.id, project)

        self.handler.unfollow(user.id, project)

        user.refresh_from_db()
        assert user.email_opt_in_competition_results is True
        assert user.email_opt_in_platform_updates is True

    def test_unfollow_when_not_following_does_not_touch_legacy(self):
        user = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        house, _, _ = _seed_house_project_with_channels()

        # Pre-condition: auto-follow signal may have followed the user on
        # UserFactory(). If so, undo to get to a clean "not following" state.
        Follow.objects.filter(user=user).delete()
        # Don't reset legacy flags — test should observe they stay True.
        User.objects.filter(pk=user.pk).update(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )

        self.handler.unfollow(user.id, house)

        user.refresh_from_db()
        assert user.email_opt_in_competition_results is True
        assert user.email_opt_in_platform_updates is True
