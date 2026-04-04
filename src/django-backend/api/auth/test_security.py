import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from api.auth.security import MODERATOR_GROUP_NAME, require_moderator

User = get_user_model()


@pytest.mark.django_db
class TestRequireModerator:
    def test_moderator_group_member_is_authorized(self):
        user = User.objects.create_user(
            email="mod@example.com", password="test", kennitala="0000000001"
        )
        group = Group.objects.get(name=MODERATOR_GROUP_NAME)
        user.groups.add(group)

        result = require_moderator(user)

        assert result is None

    def test_superuser_is_authorized(self):
        user = User.objects.create_user(
            email="super@example.com",
            password="test",
            kennitala="0000000002",
            is_superuser=True,
        )

        result = require_moderator(user)

        assert result is None

    def test_regular_user_is_denied(self):
        user = User.objects.create_user(
            email="regular@example.com", password="test", kennitala="0000000003"
        )

        result = require_moderator(user)

        assert result == (403, {"detail": "Moderator access required"})

    def test_unauthenticated_is_denied(self):
        result = require_moderator(None)

        assert result == (401, {"detail": "Authentication required"})
