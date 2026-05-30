import logging

import pytest

from apps.follows.models import Channel, Follow, FollowedChannel
from apps.follows.services import create_house_project_follow
from tests.factories import ProjectFactory, UserFactory


@pytest.fixture
def house_project_with_three_channels(db):
    project = ProjectFactory(is_house_project=True)
    # "Updates" already created by the post_save signal; add the two named ones.
    Channel.objects.get_or_create(project=project, name="Competition Winners")
    Channel.objects.get_or_create(project=project, name="Product Updates")
    return project


@pytest.mark.django_db
class TestAutoFollowOnUserCreate:
    def test_new_user_is_auto_followed(self, house_project_with_three_channels):
        house_project = house_project_with_three_channels
        user = UserFactory()
        follow = Follow.objects.get(user=user, project=house_project)
        assert FollowedChannel.objects.filter(follow=follow).count() == 3

    def test_system_user_not_auto_followed(self, house_project_with_three_channels):
        user = UserFactory(is_system_user=True)
        assert not Follow.objects.filter(user=user).exists()

    def test_no_house_project_logs_warning(self, db, caplog):
        with caplog.at_level(logging.WARNING):
            user = UserFactory()
        assert not Follow.objects.filter(user=user).exists()
        assert any(
            "no house project exists" in record.message for record in caplog.records
        )

    def test_helper_is_idempotent(self, house_project_with_three_channels):
        user = UserFactory()
        # Re-call the helper directly; should not duplicate rows.
        create_house_project_follow(user)
        assert Follow.objects.filter(user=user).count() == 1
        assert FollowedChannel.objects.filter(follow__user=user).count() == 3
