from uuid import uuid4

import pytest

from svc.users.django_impl import DjangoUserQuery
from svc.users.exceptions import UserNotFoundError
from tests.factories import UserFactory

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
    def test_returns_opted_in_platform_updates_users(self):
        opted_in = UserFactory(email_opt_in_platform_updates=True)
        UserFactory(email_opt_in_platform_updates=False)

        result = query.list_opted_in_for_broadcast_type("platform_updates")

        assert list(result) == [opted_in]

    def test_returns_opted_in_competition_results_users(self):
        opted_in = UserFactory(email_opt_in_competition_results=True)
        UserFactory(email_opt_in_competition_results=False)

        result = query.list_opted_in_for_broadcast_type("competition_results")

        assert list(result) == [opted_in]

    def test_returns_empty_for_unknown_type(self):
        UserFactory()

        result = query.list_opted_in_for_broadcast_type("unknown_type")

        assert result.count() == 0

    def test_excludes_inactive_users(self):
        UserFactory(email_opt_in_platform_updates=True, is_active=False)

        result = query.list_opted_in_for_broadcast_type("platform_updates")

        assert result.count() == 0
