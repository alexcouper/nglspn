import json
from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from hamcrest import (
    assert_that,
    contains_inanyorder,
    equal_to,
    has_entries,
    is_not,
)

from api.auth.jwt import create_access_token, create_refresh_token, verify_token
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
