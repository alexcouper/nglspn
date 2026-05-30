import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from hamcrest import (
    assert_that,
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
from tests.factories import UserFactory

User = get_user_model()


class TestRefreshToken:
    def test_refresh_with_valid_token_returns_new_access_token(
        self,
        client,
        user,
        refresh_token,
    ) -> None:
        response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": refresh_token}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(access_token=is_not(None), token_type="bearer"),
        )

        # Verify the new access token is valid
        new_token = response.json()["access_token"]
        payload = verify_token(new_token)
        assert_that(payload["user_id"], equal_to(str(user.id)))
        assert_that(payload["type"], equal_to("access"))

    def test_refresh_with_invalid_token_returns_401(self, client) -> None:
        response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": "invalid-token"}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))
        assert_that(
            response.json(),
            has_entries(detail="Invalid or expired refresh token"),
        )

    def test_refresh_with_expired_token_returns_401(self, client, user) -> None:
        # Create an expired refresh token
        payload = {
            "user_id": str(user.id),
            "exp": datetime.now(tz=UTC) - timedelta(days=1),
            "iat": datetime.now(tz=UTC) - timedelta(days=8),
            "type": "refresh",
        }
        expired_token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": expired_token}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))
        assert_that(
            response.json(),
            has_entries(detail="Invalid or expired refresh token"),
        )

    def test_refresh_with_access_token_returns_401(self, client, access_token) -> None:
        response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": access_token}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))
        assert_that(response.json(), has_entries(detail="Invalid token type"))

    def test_refresh_with_nonexistent_user_returns_401(self, client, user) -> None:
        refresh_token = create_refresh_token(user.id)
        user.delete()

        response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": refresh_token}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))
        assert_that(response.json(), has_entries(detail="User not found"))

    def test_refresh_with_inactive_user_returns_401(self, client, db) -> None:
        inactive_user = UserFactory(is_active=False)
        refresh_token = create_refresh_token(inactive_user.id)

        response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": refresh_token}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))
        assert_that(response.json(), has_entries(detail="Account is inactive"))

    def test_refresh_returns_token_for_correct_user(
        self,
        client,
        user,
        other_user,
    ) -> None:
        user_refresh = create_refresh_token(user.id)
        other_refresh = create_refresh_token(other_user.id)

        response1 = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": user_refresh}),
            content_type="application/json",
        )
        response2 = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": other_refresh}),
            content_type="application/json",
        )

        token1_payload = verify_token(response1.json()["access_token"])
        token2_payload = verify_token(response2.json()["access_token"])

        assert_that(token1_payload["user_id"], equal_to(str(user.id)))
        assert_that(token2_payload["user_id"], equal_to(str(other_user.id)))


class TestLogin:
    def test_login_returns_tokens(self, client, user) -> None:
        response = client.post(
            "/api/auth/login",
            data=json.dumps({"email": user.email, "password": "testpassword123"}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                access_token=is_not(None),
                refresh_token=is_not(None),
                token_type="bearer",
            ),
        )

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
        token = create_refresh_token(system_user.id)

        response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": token}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))

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
