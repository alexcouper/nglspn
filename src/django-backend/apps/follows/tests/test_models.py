from __future__ import annotations

import pytest
from django.db import IntegrityError

from apps.follows.models import PERSONAL_CHANNEL_NAME, Channel, Follow
from tests.factories import ProjectFactory, UserFactory, follow_user, personal_channel


@pytest.mark.django_db
class TestChannelOwnership:
    def test_channel_with_both_project_and_owner_is_rejected(self):
        with pytest.raises(IntegrityError):
            Channel.objects.create(
                project=ProjectFactory(), owner=UserFactory(), name="Both"
            )

    def test_channel_with_neither_is_rejected(self):
        with pytest.raises(IntegrityError):
            Channel.objects.create(project=None, owner=None, name="Nobody's")

    def test_a_person_may_not_have_two_channels_of_the_same_name(self):
        user = UserFactory()
        personal_channel(user)

        with pytest.raises(IntegrityError):
            Channel.objects.create(owner=user, name=PERSONAL_CHANNEL_NAME)

    def test_two_people_may_each_have_the_personal_channel(self):
        first = personal_channel(UserFactory())
        second = personal_channel(UserFactory())

        assert first.name == second.name
        assert first.pk != second.pk

    def test_signup_creates_no_channel(self):
        user = UserFactory()

        assert not Channel.objects.filter(owner=user).exists()

    def test_str_names_the_owner_when_there_is_no_project(self):
        user = UserFactory(first_name="Ada", last_name="Lovelace")

        channel = personal_channel(user)

        assert str(channel) == f"{user}: {PERSONAL_CHANNEL_NAME}"


@pytest.mark.django_db
class TestFollowTarget:
    def test_follow_with_both_targets_is_rejected(self):
        with pytest.raises(IntegrityError):
            Follow.objects.create(
                user=UserFactory(),
                project=ProjectFactory(),
                followed_user=UserFactory(),
            )

    def test_follow_with_neither_target_is_rejected(self):
        with pytest.raises(IntegrityError):
            Follow.objects.create(user=UserFactory(), project=None, followed_user=None)

    def test_self_follow_is_rejected(self):
        user = UserFactory()

        with pytest.raises(IntegrityError):
            Follow.objects.create(user=user, followed_user=user)

    def test_following_the_same_person_twice_is_rejected(self):
        follower, followed = UserFactory(), UserFactory()
        follow_user(follower, followed)

        with pytest.raises(IntegrityError):
            Follow.objects.create(user=follower, followed_user=followed)

    def test_following_the_same_project_twice_is_still_rejected(self):
        follower, project = UserFactory(), ProjectFactory()
        Follow.objects.create(user=follower, project=project)

        with pytest.raises(IntegrityError):
            Follow.objects.create(user=follower, project=project)

    def test_one_person_may_follow_a_project_and_a_person(self):
        follower = UserFactory()

        Follow.objects.create(user=follower, project=ProjectFactory())
        follow_user(follower, UserFactory())

        assert Follow.objects.filter(user=follower).count() == 2

    def test_str_names_the_followed_person(self):
        follower, followed = UserFactory(), UserFactory()

        follow = follow_user(follower, followed)

        assert str(follow) == f"{follower} → {followed}"
