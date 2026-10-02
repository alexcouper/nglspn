from datetime import UTC, datetime, timedelta

import pytest
from hamcrest import assert_that, close_to, equal_to, has_entries, is_, none, not_none

from api.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    verify_token,
)
from tests.factories import UserFactory, make_refresh_token

IDLE_LIFETIME = timedelta(days=30)
ABSOLUTE_LIFETIME = timedelta(days=365)


def assert_accepted(token, user):
    assert_that(verify_refresh_token(token, user), is_(not_none()))


def assert_rejected(token, user):
    assert_that(verify_refresh_token(token, user), is_(none()))


def seconds_since(moment):
    return (datetime.now(tz=UTC) - moment).total_seconds()


@pytest.mark.django_db
class TestCreateRefreshToken:
    def test_expires_after_the_idle_lifetime(self, user):
        claims = verify_token(create_refresh_token(user))

        lifetime = claims["exp"] - claims["iat"]
        assert_that(lifetime, equal_to(IDLE_LIFETIME.total_seconds()))

    def test_records_the_login_time_and_password_version(self, user):
        claims = verify_token(create_refresh_token(user))

        assert_that(
            claims,
            has_entries(
                type="refresh",
                user_id=str(user.id),
                auth_time=claims["iat"],
                pwv=user.get_session_auth_hash(),
            ),
        )


@pytest.mark.django_db
class TestVerifyRefreshToken:
    def test_freshly_minted_token_is_accepted(self, user):
        assert_accepted(create_refresh_token(user), user)

    def test_token_idle_for_longer_than_the_idle_lifetime_is_rejected(self, user):
        token = make_refresh_token(user, issued_ago=IDLE_LIFETIME + timedelta(days=1))

        assert_rejected(token, user)

    def test_fresh_token_from_a_login_past_the_absolute_cap_is_rejected(self, user):
        token = make_refresh_token(
            user,
            issued_ago=timedelta(days=1),
            logged_in_ago=ABSOLUTE_LIFETIME + timedelta(days=1),
        )

        assert_rejected(token, user)

    def test_fresh_token_from_a_login_inside_the_absolute_cap_is_accepted(self, user):
        token = make_refresh_token(
            user,
            issued_ago=timedelta(days=1),
            logged_in_ago=ABSOLUTE_LIFETIME - timedelta(days=1),
        )

        assert_accepted(token, user)

    def test_token_minted_before_a_password_change_is_rejected(self, user):
        token = create_refresh_token(user)

        user.set_password("a-different-password")

        assert_rejected(token, user)

    def test_token_without_a_login_time_is_rejected(self, user):
        assert_rejected(make_refresh_token(user, without=("auth_time",)), user)

    def test_token_without_a_password_version_is_rejected(self, user):
        assert_rejected(make_refresh_token(user, without=("pwv",)), user)

    def test_session_start_is_the_login_time(self, user):
        logged_in_ago = timedelta(days=100)
        token = make_refresh_token(user, logged_in_ago=logged_in_ago)

        session_start = verify_refresh_token(token, user)

        assert_that(
            seconds_since(session_start),
            close_to(logged_in_ago.total_seconds(), delta=5),
        )

    def test_login_time_is_preserved_across_reissue(self, user):
        logged_in_ago = timedelta(days=100)
        original = make_refresh_token(user, logged_in_ago=logged_in_ago)

        reissued = create_refresh_token(
            user, auth_time=verify_refresh_token(original, user)
        )

        assert_that(
            verify_token(reissued)["auth_time"],
            equal_to(verify_token(original)["auth_time"]),
        )

    def test_access_token_is_rejected(self, user):
        assert_rejected(create_access_token(user.id), user)

    def test_token_belonging_to_another_user_is_rejected(self, user):
        token = create_refresh_token(UserFactory())

        assert_rejected(token, user)

    def test_malformed_token_is_rejected(self, user):
        assert_rejected("not-a-token", user)
