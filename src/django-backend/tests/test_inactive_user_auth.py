import json

import pytest
from hamcrest import assert_that, equal_to

from api.auth.jwt import create_access_token, create_refresh_token
from tests.factories import UserFactory


@pytest.mark.django_db
class TestInactiveUserAuth:
    def test_inactive_user_login_returns_401(self, client):
        inactive = UserFactory(is_active=False)

        response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"email": inactive.email, "password": "testpassword123"},
            ),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))

    def test_inactive_user_token_refresh_returns_401(self, client):
        inactive = UserFactory(is_active=False)
        refresh = create_refresh_token(inactive.id)

        response = client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": refresh}),
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(401))

    def test_inactive_user_access_token_rejected(self, client):
        inactive = UserFactory(is_active=False)
        token = create_access_token(inactive.id)

        response = client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert_that(response.status_code, equal_to(401))
