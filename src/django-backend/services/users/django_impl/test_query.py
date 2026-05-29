from uuid import uuid4

import pytest

from services.users.django_impl import DjangoUserQuery
from services.users.exceptions import UserNotFoundError
from tests.factories import UserFactory, make_broadcast_follower

query = DjangoUserQuery()


@pytest.mark.django_db
class TestGetById:
    def test_returns_existing_user(self):
        user = UserFactory()

        result = query.get_by_id(user.id)

        assert result.id == user.id
        assert result.email == user.email

    def test_raises_for_nonexistent_user(self):
        with pytest.raises(UserNotFoundError):
            query.get_by_id(uuid4())


@pytest.mark.django_db
class TestGetActiveById:
    def test_returns_active_user(self):
        user = UserFactory(is_active=True)

        result = query.get_active_by_id(user.id)

        assert result is not None
        assert result.id == user.id

    def test_returns_none_for_inactive_user(self):
        user = UserFactory(is_active=False)

        result = query.get_active_by_id(user.id)

        assert result is None

    def test_returns_none_for_nonexistent_user(self):
        result = query.get_active_by_id(uuid4())

        assert result is None


@pytest.mark.django_db
class TestEmailExists:
    def test_true_when_email_registered(self):
        user = UserFactory(email="exists@example.com")

        assert query.email_exists(user.email) is True

    def test_false_when_email_not_registered(self):
        assert query.email_exists("nobody@example.com") is False


@pytest.mark.django_db
class TestKennitalaExists:
    def test_true_when_kennitala_registered(self):
        user = UserFactory(kennitala="1234567890")

        assert query.kennitala_exists(user.kennitala) is True

    def test_false_when_kennitala_not_registered(self):
        assert query.kennitala_exists("9999999999") is False


@pytest.mark.django_db
class TestListOptedInForBroadcastType:
    def test_returns_followers_with_email_enabled_platform_updates(self):
        follower = make_broadcast_follower("platform_updates", email_enabled=True)
        make_broadcast_follower("platform_updates", email_enabled=False)

        result = query.list_opted_in_for_broadcast_type("platform_updates")

        assert list(result) == [follower]

    def test_returns_followers_with_email_enabled_competition_results(self):
        follower = make_broadcast_follower("competition_results", email_enabled=True)
        make_broadcast_follower("competition_results", email_enabled=False)

        result = query.list_opted_in_for_broadcast_type("competition_results")

        assert list(result) == [follower]

    def test_returns_empty_for_unknown_type(self):
        make_broadcast_follower("platform_updates")

        result = query.list_opted_in_for_broadcast_type("unknown_type")

        assert result.count() == 0

    def test_returns_empty_when_no_house_project(self):
        UserFactory()

        result = query.list_opted_in_for_broadcast_type("platform_updates")

        assert result.count() == 0

    def test_excludes_inactive_users(self):
        make_broadcast_follower("platform_updates", is_active=False)

        result = query.list_opted_in_for_broadcast_type("platform_updates")

        assert result.count() == 0

    def test_excludes_system_users(self):
        make_broadcast_follower("platform_updates", is_system_user=True)

        result = query.list_opted_in_for_broadcast_type("platform_updates")

        assert result.count() == 0
