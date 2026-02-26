from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from api.auth.jwt import create_reset_token, verify_token
from apps.users.models import PasswordResetCode
from services import HANDLERS
from services.users.django_impl import PASSWORD_RESET_MAX_ATTEMPTS

from .factories import PasswordResetCodeFactory, UserFactory


@pytest.mark.django_db
class TestForgotPasswordEndpoint:
    def test_valid_email_sends_code(self, client):
        user = UserFactory()

        with patch.object(HANDLERS.email, "send_password_reset_email") as mock_send:
            response = client.post(
                "/api/auth/forgot-password",
                data={"email": user.email},
                content_type="application/json",
            )

        assert response.status_code == 200
        assert "reset code" in response.json()["message"].lower()
        assert PasswordResetCode.objects.filter(user=user).exists()
        mock_send.assert_called_once()

    def test_unknown_email_returns_same_200(self, client):
        with patch.object(HANDLERS.email, "send_password_reset_email") as mock_send:
            response = client.post(
                "/api/auth/forgot-password",
                data={"email": "nobody@example.com"},
                content_type="application/json",
            )

        assert response.status_code == 200
        assert "reset code" in response.json()["message"].lower()
        mock_send.assert_not_called()

    def test_rate_limiting_suppresses_silently(self, client):
        user = UserFactory()
        PasswordResetCodeFactory(user=user)

        with patch.object(HANDLERS.email, "send_password_reset_email") as mock_send:
            response = client.post(
                "/api/auth/forgot-password",
                data={"email": user.email},
                content_type="application/json",
            )

        assert response.status_code == 200
        mock_send.assert_not_called()
        assert PasswordResetCode.objects.filter(user=user).count() == 1


@pytest.mark.django_db
class TestForgotPasswordVerifyEndpoint:
    def test_correct_code_returns_reset_token(self, client):
        user = UserFactory()
        PasswordResetCodeFactory(user=user, code="123456")

        response = client.post(
            "/api/auth/forgot-password/verify",
            data={"email": user.email, "code": "123456"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert "reset_token" in data

        token_payload = verify_token(data["reset_token"])
        assert token_payload is not None
        assert token_payload["type"] == "reset"
        assert token_payload["user_id"] == str(user.id)

    def test_wrong_code_increments_attempts(self, client):
        user = UserFactory()
        reset_code = PasswordResetCodeFactory(user=user, code="123456")

        response = client.post(
            "/api/auth/forgot-password/verify",
            data={"email": user.email, "code": "000000"},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.json()
        assert data["attempts_remaining"] == PASSWORD_RESET_MAX_ATTEMPTS - 1

        reset_code.refresh_from_db()
        assert reset_code.attempts == 1

    def test_three_failures_exhausts_code(self, client):
        user = UserFactory()
        PasswordResetCodeFactory(
            user=user, code="123456", attempts=PASSWORD_RESET_MAX_ATTEMPTS - 1
        )

        response = client.post(
            "/api/auth/forgot-password/verify",
            data={"email": user.email, "code": "000000"},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.json()
        assert data["attempts_remaining"] == 0
        assert "new code" in data["detail"].lower()

    def test_exhausted_code_rejects_even_correct_code(self, client):
        user = UserFactory()
        PasswordResetCodeFactory(
            user=user, code="123456", attempts=PASSWORD_RESET_MAX_ATTEMPTS
        )

        response = client.post(
            "/api/auth/forgot-password/verify",
            data={"email": user.email, "code": "123456"},
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_expired_code_rejected(self, client):
        user = UserFactory()
        PasswordResetCodeFactory(
            user=user,
            code="123456",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = client.post(
            "/api/auth/forgot-password/verify",
            data={"email": user.email, "code": "123456"},
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_unknown_email_rejected(self, client):
        response = client.post(
            "/api/auth/forgot-password/verify",
            data={"email": "nobody@example.com", "code": "123456"},
            content_type="application/json",
        )

        assert response.status_code == 400


@pytest.mark.django_db
class TestResetPasswordEndpoint:
    def test_valid_reset_token_sets_password(self, client):
        user = UserFactory()
        reset_token = self._get_reset_token(client, user)

        response = client.post(
            "/api/auth/reset-password",
            data={"reset_token": reset_token, "new_password": "newpassword456"},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Password updated successfully"

        # Verify login works with new password
        login_response = client.post(
            "/api/auth/login",
            data={"email": user.email, "password": "newpassword456"},
            content_type="application/json",
        )
        assert login_response.status_code == 200

    def test_expired_reset_token_rejected(self, client):
        response = client.post(
            "/api/auth/reset-password",
            data={"reset_token": "expired.token.here", "new_password": "newpass123"},
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_access_token_rejected_as_reset_token(self, client):
        user = UserFactory()

        login_response = client.post(
            "/api/auth/login",
            data={"email": user.email, "password": "testpassword123"},
            content_type="application/json",
        )
        access_token = login_response.json()["access_token"]

        response = client.post(
            "/api/auth/reset-password",
            data={"reset_token": access_token, "new_password": "newpass123"},
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "token type" in response.json()["detail"].lower()

    def test_missing_reset_token_rejected(self, client):
        response = client.post(
            "/api/auth/reset-password",
            data={"reset_token": "", "new_password": "newpass123"},
            content_type="application/json",
        )

        assert response.status_code == 400

    def _get_reset_token(self, client, user):
        PasswordResetCodeFactory(user=user, code="999999")

        response = client.post(
            "/api/auth/forgot-password/verify",
            data={"email": user.email, "code": "999999"},
            content_type="application/json",
        )
        return response.json()["reset_token"]


@pytest.mark.django_db
class TestResetTokenCannotAccessProtectedEndpoints:
    def test_reset_token_rejected_by_me_endpoint(self, client):
        user = UserFactory()
        reset_token = create_reset_token(str(user.id))

        response = client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {reset_token}",
        )

        assert response.status_code == 401

    def test_refresh_token_rejected_by_me_endpoint(self, client):
        user = UserFactory()

        login_response = client.post(
            "/api/auth/login",
            data={"email": user.email, "password": "testpassword123"},
            content_type="application/json",
        )
        refresh_token = login_response.json()["refresh_token"]

        response = client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {refresh_token}",
        )

        assert response.status_code == 401


@pytest.mark.django_db
class TestPasswordResetEndToEnd:
    def test_full_flow_request_verify_reset_login(self, client):
        user = UserFactory()

        # Step 1: Request reset code
        with patch.object(HANDLERS.email, "send_password_reset_email"):
            response = client.post(
                "/api/auth/forgot-password",
                data={"email": user.email},
                content_type="application/json",
            )
        assert response.status_code == 200

        # Get the code from the database
        reset_code = PasswordResetCode.objects.filter(user=user).latest("created_at")

        # Step 2: Verify code
        response = client.post(
            "/api/auth/forgot-password/verify",
            data={"email": user.email, "code": reset_code.code},
            content_type="application/json",
        )
        assert response.status_code == 200
        reset_token = response.json()["reset_token"]

        # Step 3: Reset password
        response = client.post(
            "/api/auth/reset-password",
            data={"reset_token": reset_token, "new_password": "brandnewpassword"},
            content_type="application/json",
        )
        assert response.status_code == 200

        # Step 4: Login with new password
        response = client.post(
            "/api/auth/login",
            data={"email": user.email, "password": "brandnewpassword"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

        # Verify old password no longer works
        response = client.post(
            "/api/auth/login",
            data={"email": user.email, "password": "testpassword123"},
            content_type="application/json",
        )
        assert response.status_code == 401
