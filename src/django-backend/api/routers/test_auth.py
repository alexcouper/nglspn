import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.utils import timezone
from hamcrest import (
    assert_that,
    close_to,
    contains_inanyorder,
    equal_to,
    has_entries,
    has_key,
    is_not,
    not_,
)

from api.auth.jwt import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    verify_token,
)
from apps.users.models import PasswordResetCode
from tests.assertions import (
    assert_clears_refresh_cookie,
    assert_leaves_refresh_cookie_alone,
    assert_sets_refresh_cookie,
    refresh_cookie,
)
from tests.factories import UserFactory, make_refresh_token

User = get_user_model()


IDLE_LIFETIME = timedelta(days=30)
ABSOLUTE_LIFETIME = timedelta(days=365)


def log_in(client, user, password="testpassword123"):  # noqa: S107
    return client.post(
        "/api/auth/login",
        data=json.dumps({"email": user.email, "password": password}),
        content_type="application/json",
    )


def post_without_body(client, path):
    # What the web UI sends: a JSON content type and nothing else. A bare
    # `client.post(path)` would send an empty multipart form instead.
    return client.post(path, data="", content_type="application/json")


def refresh_with_cookie(client, token):
    client.cookies[settings.REFRESH_COOKIE_NAME] = token
    return post_without_body(client, "/api/auth/refresh")


def reset_password(client, user, new_password):
    return client.post(
        "/api/auth/reset-password",
        data=json.dumps(
            {
                "reset_token": create_reset_token(user.id),
                "new_password": new_password,
            }
        ),
        content_type="application/json",
    )


def reissued_refresh_claims(response):
    return verify_token(refresh_cookie(response).value)


def assert_refreshed_for(response, user) -> None:
    assert_that(response.status_code, equal_to(200))
    assert_that(response.json(), has_entries(token_type="bearer"))
    assert_that(
        verify_token(response.json()["access_token"]),
        has_entries(user_id=str(user.id), type="access"),
    )
    assert_sets_refresh_cookie(response)
    assert_that(
        reissued_refresh_claims(response),
        has_entries(user_id=str(user.id), type="refresh"),
    )


def assert_refresh_rejected(response, detail=None) -> None:
    assert_that(response.status_code, equal_to(401))
    if detail is not None:
        assert_that(response.json(), has_entries(detail=detail))
    assert_leaves_refresh_cookie_alone(response)


class TestRefreshToken:
    def test_refresh_with_cookie_and_no_body_returns_new_tokens(
        self, client, user, refresh_token
    ) -> None:
        response = refresh_with_cookie(client, refresh_token)

        assert_refreshed_for(response, user)

    def test_refresh_does_not_return_the_refresh_token_in_the_body(
        self, client, refresh_token
    ) -> None:
        response = refresh_with_cookie(client, refresh_token)

        assert_that(response.json(), not_(has_key("refresh_token")))

    def test_refresh_pushes_the_idle_expiry_out_again(self, client, user) -> None:
        nearly_expired = make_refresh_token(
            user, issued_ago=IDLE_LIFETIME - timedelta(days=1)
        )

        response = refresh_with_cookie(client, nearly_expired)

        claims = reissued_refresh_claims(response)
        expires_in = claims["exp"] - datetime.now(tz=UTC).timestamp()
        assert_that(expires_in, close_to(IDLE_LIFETIME.total_seconds(), delta=60))

    def test_refresh_carries_the_original_login_time_forward(
        self, client, user
    ) -> None:
        token = make_refresh_token(
            user, issued_ago=timedelta(days=20), logged_in_ago=timedelta(days=100)
        )

        response = refresh_with_cookie(client, token)

        assert_that(
            reissued_refresh_claims(response)["auth_time"],
            equal_to(verify_token(token)["auth_time"]),
        )

    def test_refresh_without_any_token_returns_401(self, client, db) -> None:
        response = post_without_body(client, "/api/auth/refresh")

        assert_refresh_rejected(response, "Invalid or expired refresh token")

    def test_token_in_the_body_is_ignored(self, client, refresh_token) -> None:
        response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": refresh_token}),
            content_type="application/json",
        )

        assert_refresh_rejected(response, "Invalid or expired refresh token")

    def test_refresh_with_invalid_token_returns_401(self, client, db) -> None:
        response = refresh_with_cookie(client, "invalid-token")

        assert_refresh_rejected(response, "Invalid or expired refresh token")

    def test_refresh_with_idle_expired_token_returns_401(self, client, user) -> None:
        expired = make_refresh_token(user, issued_ago=IDLE_LIFETIME + timedelta(days=1))

        response = refresh_with_cookie(client, expired)

        assert_refresh_rejected(response, "Invalid or expired refresh token")

    def test_refresh_past_the_absolute_cap_returns_401_despite_fresh_token(
        self, client, user
    ) -> None:
        capped = make_refresh_token(
            user,
            issued_ago=timedelta(days=1),
            logged_in_ago=ABSOLUTE_LIFETIME + timedelta(days=1),
        )

        response = refresh_with_cookie(client, capped)

        assert_refresh_rejected(response, "Invalid or expired refresh token")

    def test_refresh_with_access_token_returns_401(self, client, access_token) -> None:
        response = refresh_with_cookie(client, access_token)

        assert_refresh_rejected(response, "Invalid or expired refresh token")

    def test_refresh_with_nonexistent_user_returns_401(self, client, user) -> None:
        refresh_token = create_refresh_token(user)
        user.delete()

        response = refresh_with_cookie(client, refresh_token)

        assert_refresh_rejected(response, "User not found")

    def test_refresh_with_inactive_user_returns_401(self, client, db) -> None:
        inactive_user = UserFactory(is_active=False)

        response = refresh_with_cookie(client, create_refresh_token(inactive_user))

        assert_refresh_rejected(response, "Account is inactive")

    def test_same_token_refreshed_from_two_tabs_succeeds_for_both(
        self, user, refresh_token
    ) -> None:
        # Nothing is rotated away: the token stays good until its own expiry,
        # so the second tab is not rejected because the first got there first.
        first_tab, second_tab = Client(), Client()

        first = refresh_with_cookie(first_tab, refresh_token)
        second = refresh_with_cookie(second_tab, refresh_token)

        assert_refreshed_for(first, user)
        assert_refreshed_for(second, user)

    def test_reissued_cookie_refreshes_again(self, client, user, refresh_token) -> None:
        refresh_with_cookie(client, refresh_token)

        # The client now carries the cookie the first refresh set.
        response = post_without_body(client, "/api/auth/refresh")

        assert_refreshed_for(response, user)


class TestLogout:
    def test_logout_with_cookie_expires_it(self, client, refresh_token) -> None:
        client.cookies[settings.REFRESH_COOKIE_NAME] = refresh_token

        response = post_without_body(client, "/api/auth/logout")

        assert_that(response.status_code, equal_to(204))
        assert_clears_refresh_cookie(response)

    def test_logout_without_cookie_succeeds(self, client) -> None:
        response = post_without_body(client, "/api/auth/logout")

        assert_that(response.status_code, equal_to(204))

    def test_logout_needs_no_access_token(self, client, user) -> None:
        log_in(client, user)

        response = post_without_body(client, "/api/auth/logout")

        assert_that(response.status_code, equal_to(204))
        assert_clears_refresh_cookie(response)

    def test_logout_does_not_revoke_the_token_itself(
        self, client, user, refresh_token
    ) -> None:
        # Stateless: logout only removes the cookie from the browser. A copy of
        # the old value stays good until its own expiry.
        client.cookies[settings.REFRESH_COOKIE_NAME] = refresh_token
        post_without_body(client, "/api/auth/logout")

        response = refresh_with_cookie(Client(), refresh_token)

        assert_refreshed_for(response, user)


class TestPasswordResetEndsOtherSessions:
    def test_refresh_token_minted_before_reset_is_rejected(self, client, user) -> None:
        token_from_before = create_refresh_token(user)

        reset_password(client, user, "a-new-password-123")
        response = refresh_with_cookie(client, token_from_before)

        assert_refresh_rejected(response, "Invalid or expired refresh token")

    def test_refresh_token_from_login_after_reset_works(self, client, user) -> None:
        reset_password(client, user, "a-new-password-123")
        log_in(client, user, "a-new-password-123")

        # The client now carries the cookie the login set.
        response = post_without_body(client, "/api/auth/refresh")

        assert_refreshed_for(response, user)

    def test_access_token_minted_before_reset_keeps_working(
        self, client, user, auth_headers
    ) -> None:
        reset_password(client, user, "a-new-password-123")

        response = client.get("/api/auth/me", **auth_headers)

        assert_that(response.status_code, equal_to(200))


# A page on another site can make the victim's browser submit a login for the
# attacker's account. Nothing in the response is readable to it, but the
# Set-Cookie would be stored first-party and the victim would be operating the
# attacker's account from then on. Two independent layers stop it.
class TestCrossSiteLogin:
    def test_form_post_with_valid_credentials_is_refused_and_sets_no_cookie(
        self, client, user
    ) -> None:
        # What `<form enctype="text/plain">` delivers: a JSON-shaped body under a
        # content type a form can send, with no CORS preflight. The form field
        # name is everything before the `=`, the value the trailing `"}`.
        body = f'{{"email":"{user.email}","password":"testpassword123","x":"="}}'
        response = client.post("/api/auth/login", data=body, content_type="text/plain")

        assert_that(response.status_code, equal_to(400))
        assert_leaves_refresh_cookie_alone(response)

    def test_urlencoded_form_post_is_refused(self, client, user) -> None:
        response = client.post(
            "/api/auth/login",
            data={"email": user.email, "password": "testpassword123"},
        )

        assert_that(response.status_code, equal_to(400))
        assert_leaves_refresh_cookie_alone(response)

    def test_browser_marked_cross_site_request_is_refused(self, client, user) -> None:
        response = client.post(
            "/api/auth/login",
            data=json.dumps({"email": user.email, "password": "testpassword123"}),
            content_type="application/json",
            headers={"Sec-Fetch-Site": "cross-site"},
        )

        assert_that(response.status_code, equal_to(403))
        assert_leaves_refresh_cookie_alone(response)

    def test_same_site_request_is_allowed(self, client, user) -> None:
        response = client.post(
            "/api/auth/login",
            data=json.dumps({"email": user.email, "password": "testpassword123"}),
            content_type="application/json",
            headers={"Sec-Fetch-Site": "same-site"},
        )

        assert_that(response.status_code, equal_to(200))
        assert_sets_refresh_cookie(response)

    def test_cross_site_refresh_is_refused(self, client, refresh_token) -> None:
        client.cookies[settings.REFRESH_COOKIE_NAME] = refresh_token

        response = client.post(
            "/api/auth/refresh",
            data="",
            content_type="application/json",
            headers={"Sec-Fetch-Site": "cross-site"},
        )

        assert_that(response.status_code, equal_to(403))
        assert_leaves_refresh_cookie_alone(response)

    def test_cross_site_logout_is_refused(self, client, refresh_token) -> None:
        client.cookies[settings.REFRESH_COOKIE_NAME] = refresh_token

        response = client.post(
            "/api/auth/logout",
            data="",
            content_type="application/json",
            headers={"Sec-Fetch-Site": "cross-site"},
        )

        assert_that(response.status_code, equal_to(403))
        assert_leaves_refresh_cookie_alone(response)


class TestLogin:
    def test_login_returns_access_token_and_no_refresh_token_in_body(
        self, client, user
    ) -> None:
        response = log_in(client, user)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                access_token=is_not(None),
                token_type="bearer",
                is_verified=True,
            ),
        )
        assert_that(response.json(), not_(has_key("refresh_token")))

    def test_login_sets_the_refresh_token_cookie(self, client, user) -> None:
        response = log_in(client, user)

        assert_sets_refresh_cookie(response)
        assert_that(
            reissued_refresh_claims(response),
            has_entries(user_id=str(user.id), type="refresh"),
        )

    def test_failed_login_sets_no_cookie(self, client, user) -> None:
        response = log_in(client, user, "wrongpassword")

        assert_that(response.status_code, equal_to(401))
        assert_leaves_refresh_cookie_alone(response)

    def test_login_with_invalid_credentials_returns_401(self, client, user) -> None:
        response = client.post(
            "/api/auth/login",
            data=json.dumps({"email": user.email, "password": "wrongpassword"}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))
        assert_that(response.json(), has_entries(detail="Invalid credentials"))

    def test_login_with_inactive_user_returns_401(self, client, db) -> None:
        # Django's authenticate() returns None for inactive users,
        # so they get the same error as invalid credentials
        inactive_user = UserFactory(is_active=False)

        response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"email": inactive_user.email, "password": "testpassword123"},
            ),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))

    def test_login_with_system_user_returns_401(self, client, db) -> None:
        # System users must not be able to log in even with the correct password.
        system_user = UserFactory(is_system_user=True)

        response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"email": system_user.email, "password": "testpassword123"},
            ),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))
        assert_that(response.json(), has_entries(detail="Invalid credentials"))


@pytest.mark.django_db
class TestSystemUserAuthGates:
    def test_refresh_token_rejects_system_user(self, client) -> None:
        system_user = UserFactory(is_system_user=True)

        response = refresh_with_cookie(client, create_refresh_token(system_user))

        assert_refresh_rejected(response)

    def test_access_token_for_system_user_does_not_authenticate(self, client) -> None:
        system_user = UserFactory(is_system_user=True)
        token = create_access_token(system_user.id)

        response = client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert_that(response.status_code, equal_to(401))

    def test_forgot_password_does_not_create_code_for_system_user(
        self, client, db
    ) -> None:
        system_user = UserFactory(is_system_user=True)

        response = client.post(
            "/api/auth/forgot-password",
            data=json.dumps({"email": system_user.email}),
            content_type="application/json",
        )

        # Generic response either way (do not disclose existence)
        assert_that(response.status_code, equal_to(200))
        # But no reset code is created.
        assert_that(
            PasswordResetCode.objects.filter(user=system_user).exists(),
            equal_to(False),
        )

    def test_forgot_password_verify_rejects_system_user(self, client, db) -> None:
        system_user = UserFactory(is_system_user=True)
        # Force-create a reset code (bypassing the create gate) to confirm the
        # verify path also rejects.
        PasswordResetCode.objects.create(
            user=system_user,
            code="000000",
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        response = client.post(
            "/api/auth/forgot-password/verify",
            data=json.dumps({"email": system_user.email, "code": "000000"}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(400))

    def test_reset_password_rejects_system_user(self, client, db) -> None:
        # Defense-in-depth: if a reset token is somehow minted for a system
        # user, the reset endpoint must still refuse.
        system_user = UserFactory(is_system_user=True)
        token = create_reset_token(system_user.id)

        response = client.post(
            "/api/auth/reset-password",
            data=json.dumps({"reset_token": token, "new_password": "newpassword123"}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(400))

    def test_resend_verification_rejects_system_user(self, client, db) -> None:
        # `create_verification_code` itself is not gated; reachability is
        # blocked upstream because every entry point is auth-gated and
        # system users cannot pass the JWT auth check.
        system_user = UserFactory(is_system_user=True, is_verified=False)
        token = create_access_token(system_user.id)

        response = client.post(
            "/api/auth/resend-verification",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert_that(response.status_code, equal_to(401))


class TestGetCurrentUser:
    def test_get_current_user_returns_user_info(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        response = client.get("/api/auth/me", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                id=str(user.id),
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
            ),
        )

    def test_verified_user_has_no_pending_onboarding_steps(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        response = client.get("/api/auth/me", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(pending_onboarding_steps=[]))

    def test_unverified_user_has_verify_email_pending_step(self, client, db) -> None:
        unverified = UserFactory(is_verified=False)
        token = create_access_token(unverified.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        response = client.get("/api/auth/me", **headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(pending_onboarding_steps=["verify-email"]),
        )

    def test_get_current_user_without_auth_returns_401(self, client) -> None:
        response = client.get("/api/auth/me")

        assert_that(response.status_code, equal_to(401))

    def test_get_current_user_with_expired_token_returns_401(
        self,
        client,
        user,
    ) -> None:
        payload = {
            "user_id": str(user.id),
            "exp": datetime.now(tz=UTC) - timedelta(minutes=1),
            "iat": datetime.now(tz=UTC) - timedelta(minutes=31),
            "type": "access",
        }
        expired_token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        response = client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {expired_token}",
        )

        assert_that(response.status_code, equal_to(401))

    def test_get_current_user_returns_empty_groups_when_user_has_none(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        response = client.get("/api/auth/me", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(groups=[]))

    def test_get_current_user_returns_group_names(self, client, db) -> None:
        reviewers, _ = Group.objects.get_or_create(name="reviewers")
        editors, _ = Group.objects.get_or_create(name="editors")

        user = UserFactory()
        user.groups.add(reviewers, editors)

        token = create_access_token(user.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        response = client.get("/api/auth/me", **headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["groups"],
            contains_inanyorder("reviewers", "editors"),
        )


class TestUpdateCurrentUser:
    def test_update_first_name(self, client, user, auth_headers) -> None:
        response = client.put(
            "/api/auth/me",
            data=json.dumps({"first_name": "NewFirst"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(first_name="NewFirst"))

        user.refresh_from_db()
        assert_that(user.first_name, equal_to("NewFirst"))

    def test_update_last_name(self, client, user, auth_headers) -> None:
        response = client.put(
            "/api/auth/me",
            data=json.dumps({"last_name": "NewLast"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(last_name="NewLast"))

        user.refresh_from_db()
        assert_that(user.last_name, equal_to("NewLast"))

    def test_update_info(self, client, user, auth_headers) -> None:
        response = client.put(
            "/api/auth/me",
            data=json.dumps({"info": "I am a software developer from Iceland."}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(info="I am a software developer from Iceland."),
        )

        user.refresh_from_db()
        assert_that(user.info, equal_to("I am a software developer from Iceland."))

    def test_update_multiple_fields(self, client, user, auth_headers) -> None:
        response = client.put(
            "/api/auth/me",
            data=json.dumps(
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "info": "Full stack developer",
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                first_name="John",
                last_name="Doe",
                info="Full stack developer",
            ),
        )

        user.refresh_from_db()
        assert_that(user.first_name, equal_to("John"))
        assert_that(user.last_name, equal_to("Doe"))
        assert_that(user.info, equal_to("Full stack developer"))

    def test_update_without_auth_returns_401(self, client) -> None:
        response = client.put(
            "/api/auth/me",
            data=json.dumps({"first_name": "NewFirst"}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))

    def test_update_discussion_email_frequency_with_valid_value(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        response = client.put(
            "/api/auth/me",
            data=json.dumps({"discussion_email_frequency": "immediate"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(discussion_email_frequency="immediate"),
        )

        user.refresh_from_db()
        assert_that(user.discussion_email_frequency, equal_to("immediate"))

    def test_update_article_email_frequency_with_valid_value(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        response = client.put(
            "/api/auth/me",
            data=json.dumps({"article_email_frequency": "weekly"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(article_email_frequency="weekly"))

        user.refresh_from_db()
        assert_that(user.article_email_frequency, equal_to("weekly"))

    def test_update_discussion_email_frequency_with_invalid_value_returns_422(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        response = client.put(
            "/api/auth/me",
            data=json.dumps({"discussion_email_frequency": "banana"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(422))

    def test_article_email_frequency_rejects_immediate(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        # `immediate` is discussion-only — articles always go through a digest.
        response = client.put(
            "/api/auth/me",
            data=json.dumps({"article_email_frequency": "immediate"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(422))

    def test_partial_update_preserves_other_fields(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        user.first_name = "Original"
        user.last_name = "Name"
        user.info = "Original info"
        user.save()

        response = client.put(
            "/api/auth/me",
            data=json.dumps({"info": "Updated info"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))

        user.refresh_from_db()
        assert_that(user.first_name, equal_to("Original"))
        assert_that(user.last_name, equal_to("Name"))
        assert_that(user.info, equal_to("Updated info"))

    def test_update_with_at_least_one_name_succeeds(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        response = client.put(
            "/api/auth/me",
            data=json.dumps({"first_name": "Jane", "last_name": ""}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(first_name="Jane"))

    def test_update_clearing_both_names_returns_400(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        user.first_name = "Jane"
        user.last_name = "Doe"
        user.save()

        response = client.put(
            "/api/auth/me",
            data=json.dumps({"first_name": "", "last_name": ""}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))

    def test_partial_update_with_existing_names_preserved_succeeds(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        user.first_name = "Jane"
        user.last_name = ""
        user.save()

        response = client.put(
            "/api/auth/me",
            data=json.dumps({"discussion_email_frequency": "immediate"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))


@pytest.mark.django_db
class TestKennitalaNotExposed:
    def test_me_does_not_return_kennitala(self, client, user, auth_headers) -> None:
        response = client.get("/api/auth/me", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), not_(has_key("kennitala")))

    def test_register_does_not_return_kennitala(self, client, db) -> None:
        response = client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "email": "newuser@example.com",
                    "password": "securepassword123",
                    "kennitala": "1234567890",
                    "first_name": "Test",
                    "last_name": "User",
                }
            ),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(201))
        assert_that(response.json(), not_(has_key("kennitala")))


@pytest.mark.django_db
class TestLoginRateLimit:
    def test_login_rate_limited_after_max_attempts(self, client, user) -> None:
        for i in range(5):
            client.post(
                "/api/auth/login",
                data=json.dumps({"email": user.email, "password": f"wrongpassword{i}"}),
                content_type="application/json",
            )

        # 6th attempt should be rate limited
        response = client.post(
            "/api/auth/login",
            data=json.dumps({"email": user.email, "password": "wrongpassword"}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(429))


@pytest.mark.django_db
class TestVerifyEmailRateLimit:
    def test_verify_email_rate_limited(self, client, user, auth_headers) -> None:
        for i in range(5):
            client.post(
                "/api/auth/verify-email",
                data=json.dumps({"code": f"{i:06d}"}),
                content_type="application/json",
                **auth_headers,
            )

        # 6th attempt should be rate limited
        response = client.post(
            "/api/auth/verify-email",
            data=json.dumps({"code": "999999"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(429))


@pytest.mark.django_db
class TestUserEnumeration:
    def test_register_existing_email_generic_error(self, client, user) -> None:
        response = client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "email": user.email,
                    "password": "securepassword123",
                    "kennitala": "9999999999",
                    "first_name": "Test",
                    "last_name": "User",
                }
            ),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json(),
            has_entries(
                detail="Registration failed."
                " Please check your information and try again."
            ),
        )

    def test_register_existing_kennitala_generic_error(self, client, user) -> None:
        response = client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "email": "unique@example.com",
                    "password": "securepassword123",
                    "kennitala": user.kennitala,
                    "first_name": "Test",
                    "last_name": "User",
                }
            ),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json(),
            has_entries(
                detail="Registration failed."
                " Please check your information and try again."
            ),
        )

    def test_login_inactive_same_as_invalid(self, client, db) -> None:
        inactive_user = UserFactory(is_active=False)

        response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"email": inactive_user.email, "password": "testpassword123"},
            ),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))
        assert_that(response.json(), has_entries(detail="Invalid credentials"))
