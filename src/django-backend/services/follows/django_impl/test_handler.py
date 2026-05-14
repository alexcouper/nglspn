import pytest

from apps.follows.models import Channel, Follow, FollowChannelPreference
from services.follows.django_impl.handler import DjangoFollowHandler
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
