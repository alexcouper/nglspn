from importlib import import_module

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.users.seed import (
    COMMUNITY_USER_EMAIL,
    COMMUNITY_USER_INFO,
    COMMUNITY_USER_KENNITALA,
    get_community_user,
)
from tests.factories import UserFactory


@pytest.mark.django_db
class TestIsSystemUserField:
    def test_default_is_false(self):
        user = UserFactory()
        assert user.is_system_user is False

    def test_setting_true_does_not_change_other_fields(self):
        user = UserFactory(is_active=True, is_verified=True)
        user.is_system_user = True
        user.save()
        user.refresh_from_db()
        assert user.is_system_user is True
        assert user.is_active is True
        assert user.is_verified is True


seed_migration = import_module("apps.users.migrations.0015_community_user_seed")


@pytest.mark.django_db
class TestCommunityUserSeed:
    def _delete_seed(self):
        get_user_model().objects.filter(kennitala=COMMUNITY_USER_KENNITALA).delete()

    def _run_forward(self):
        seed_migration.create_community_user(django_apps, schema_editor=None)

    def test_creates_seed_user_with_documented_properties(self):
        self._delete_seed()

        self._run_forward()

        user_model = get_user_model()
        user = user_model.objects.get(kennitala=COMMUNITY_USER_KENNITALA)
        assert user.email == COMMUNITY_USER_EMAIL
        assert user.is_system_user is True
        assert user.is_active is True
        assert user.is_verified is True
        assert user.info == COMMUNITY_USER_INFO
        assert user.has_usable_password() is False

    def test_is_idempotent(self):
        self._delete_seed()

        self._run_forward()
        self._run_forward()

        user_model = get_user_model()
        assert (
            user_model.objects.filter(kennitala=COMMUNITY_USER_KENNITALA).count() == 1
        )

    def test_management_command_ensures_seed(self):
        self._delete_seed()

        call_command("ensure_community_user")

        user_model = get_user_model()
        assert user_model.objects.filter(kennitala=COMMUNITY_USER_KENNITALA).exists()

    def test_get_community_user_returns_seed(self):
        # The seed migration runs as part of test DB setup.
        user = get_community_user()
        assert user.kennitala == COMMUNITY_USER_KENNITALA
        assert user.is_system_user is True

    def test_get_community_user_raises_when_missing(self):
        self._delete_seed()

        with pytest.raises(RuntimeError):
            get_community_user()
