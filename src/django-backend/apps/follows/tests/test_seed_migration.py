from importlib import import_module

import pytest
from django.apps import apps as django_apps

from apps.follows.models import Channel, Follow, FollowChannelPreference
from apps.projects.models import Project
from tests.factories import ProjectFactory, UserFactory

migration_module = import_module(
    "apps.follows.migrations.0002_seed_channels_and_house_follows"
)


def _run_forward():
    migration_module.seed_channels_and_house_follows(django_apps, schema_editor=None)


def _run_reverse():
    migration_module.reverse_seed(django_apps, schema_editor=None)


@pytest.mark.django_db
class TestSeedMigration:
    def test_no_house_project_is_noop(self):
        _run_forward()
        assert not Project.objects.filter(is_house_project=True).exists()

    def test_naglasupan_gets_three_channels_and_flag_flips(self):
        naglasupan = ProjectFactory(slug="naglasupan", title="Naglasúpan")
        # Pre-migration: created via factory, so the post_save signal already
        # made the "Updates" channel. is_house_project is still False.
        assert not naglasupan.is_house_project

        _run_forward()

        naglasupan.refresh_from_db()
        assert naglasupan.is_house_project is True
        names = set(
            Channel.objects.filter(project=naglasupan).values_list("name", flat=True)
        )
        assert names == {"Updates", "Competition Winners", "Product Updates"}

    def test_other_projects_get_only_updates(self):
        ProjectFactory(slug="naglasupan")
        other = ProjectFactory(slug="other-project")
        # Other already has Updates from the signal — migration must not
        # duplicate.
        _run_forward()

        names = list(
            Channel.objects.filter(project=other).values_list("name", flat=True)
        )
        assert names == ["Updates"]

    def test_opted_out_user_has_email_disabled(self):
        # Create users *before* the house project exists, so the auto-follow
        # signal no-ops and the migration is the only path that creates Follow
        # rows for them. This mirrors prod: users existed long before the
        # house flag did.
        opted_out = UserFactory(
            email_opt_in_competition_results=False,
            email_opt_in_platform_updates=True,
        )
        opted_in = UserFactory(
            email_opt_in_competition_results=True,
            email_opt_in_platform_updates=True,
        )
        # Now create the house project — auto-follow fires *for none* of the
        # existing users (signal only triggers on user create).
        ProjectFactory(slug="naglasupan", title="Naglasúpan")

        _run_forward()

        out_follow = Follow.objects.get(user=opted_out)
        prefs = {
            p.channel.name: p
            for p in FollowChannelPreference.objects.filter(follow=out_follow)
        }
        assert prefs["Competition Winners"].email_enabled is False
        assert prefs["Product Updates"].email_enabled is True
        assert prefs["Updates"].email_enabled is True
        for p in prefs.values():
            assert p.in_app_enabled is True

        in_follow = Follow.objects.get(user=opted_in)
        in_prefs = {
            p.channel.name: p
            for p in FollowChannelPreference.objects.filter(follow=in_follow)
        }
        assert in_prefs["Competition Winners"].email_enabled is True
        assert in_prefs["Product Updates"].email_enabled is True

    def test_inactive_and_system_users_skipped(self):
        inactive = UserFactory(is_active=False)
        system = UserFactory(is_system_user=True)
        # ProjectFactory's SubFactory creator adds one eligible user — that one
        # is expected to be backfilled. We only assert the skipped pair.
        ProjectFactory(slug="naglasupan")

        _run_forward()

        assert not Follow.objects.filter(user=inactive).exists()
        assert not Follow.objects.filter(user=system).exists()

    def test_migration_is_idempotent(self):
        user = UserFactory()
        ProjectFactory(slug="naglasupan")

        _run_forward()
        _run_forward()

        assert Follow.objects.filter(user=user).count() == 1
        assert FollowChannelPreference.objects.filter(follow__user=user).count() == 3

    def test_reverse_clears_house_state(self):
        user = UserFactory()
        ProjectFactory(slug="naglasupan")
        _run_forward()
        assert Follow.objects.filter(user=user).exists()

        _run_reverse()

        assert Follow.objects.count() == 0
        assert FollowChannelPreference.objects.count() == 0
        naglasupan = Project.objects.get(slug="naglasupan")
        assert naglasupan.is_house_project is False
        # No channels left on Naglasúpan after reverse — including Updates.
        assert not Channel.objects.filter(project=naglasupan).exists()
