from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from api.auth.jwt import create_access_token
from apps.users.models import EmailVerificationCode
from services import HANDLERS
from services.users.django_impl import (
    VERIFICATION_COOLDOWN_SECONDS,
    generate_verification_code,
)

from .factories import EmailVerificationCodeFactory, UserFactory


class TestGenerateVerificationCode:
    def test_generates_6_digit_code(self):
        code = generate_verification_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_generates_different_codes(self):
        codes = {generate_verification_code() for _ in range(100)}
        assert len(codes) > 1


@pytest.mark.django_db
class TestRegistrationSendsVerificationEmail:
    def test_sends_email_on_registration(self, client):
        with patch.object(HANDLERS.email, "send_verification_email") as mock_send:
            response = client.post(
                "/api/auth/register",
                data={
                    "email": "newuser@example.com",
                    "password": "testpassword123",
                    "first_name": "New",
                    "last_name": "User",
                    "kennitala": "1234567890",
                },
                content_type="application/json",
            )

            assert response.status_code == 201
            mock_send.assert_called_once()
            assert EmailVerificationCode.objects.filter(
                user__email="newuser@example.com"
            ).exists()


@pytest.mark.django_db
class TestLoginVerificationBehavior:
    def test_returns_is_verified_true_for_verified_user(self, client):
        user = UserFactory(is_verified=True)

        response = client.post(
            "/api/auth/login",
            data={"email": user.email, "password": "testpassword123"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_verified"] is True

    def test_returns_is_verified_false_for_unverified_user(self, client):
        user = UserFactory(is_verified=False)

        with patch.object(HANDLERS.email, "send_verification_email"):
            response = client.post(
                "/api/auth/login",
                data={"email": user.email, "password": "testpassword123"},
                content_type="application/json",
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_verified"] is False

    def test_sends_verification_email_for_unverified_user(self, client):
        user = UserFactory(is_verified=False)

        with patch.object(HANDLERS.email, "send_verification_email") as mock_send:
            client.post(
                "/api/auth/login",
                data={"email": user.email, "password": "testpassword123"},
                content_type="application/json",
            )

            mock_send.assert_called_once()

    def test_does_not_send_email_for_verified_user(self, client):
        user = UserFactory(is_verified=True)

        with patch.object(HANDLERS.email, "send_verification_email") as mock_send:
            client.post(
                "/api/auth/login",
                data={"email": user.email, "password": "testpassword123"},
                content_type="application/json",
            )

            mock_send.assert_not_called()


@pytest.mark.django_db
class TestVerifyEmailEndpoint:
    def test_verifies_valid_code(self, client):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(user=user, code="123456")
        token = self._get_token(client, user)

        response = client.post(
            "/api/auth/verify-email",
            data={"code": "123456"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_verified"] is True
        assert data["message"] == "Email verified successfully"

    def test_rejects_invalid_code(self, client):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(user=user, code="123456")
        token = self._get_token(client, user)

        response = client.post(
            "/api/auth/verify-email",
            data={"code": "000000"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired verification code"

    def test_returns_already_verified(self, client):
        user = UserFactory(is_verified=True)
        token = self._get_token(client, user)

        response = client.post(
            "/api/auth/verify-email",
            data={"code": "123456"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_verified"] is True
        assert data["message"] == "Email already verified"

    def test_requires_authentication(self, client):
        response = client.post(
            "/api/auth/verify-email",
            data={"code": "123456"},
            content_type="application/json",
        )

        assert response.status_code == 401

    def _get_token(self, client, user):
        return create_access_token(user.id)


@pytest.mark.django_db
class TestResendVerificationEndpoint:
    def test_sends_verification_email(self, client):
        user = UserFactory(is_verified=False)
        token = self._get_token(client, user)

        # Wait for cooldown to pass
        cooldown_offset = timedelta(seconds=VERIFICATION_COOLDOWN_SECONDS + 1)
        EmailVerificationCode.objects.filter(user=user).update(
            created_at=timezone.now() - cooldown_offset
        )

        with patch.object(HANDLERS.email, "send_verification_email") as mock_send:
            response = client.post(
                "/api/auth/resend-verification",
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            assert response.status_code == 200
            assert response.json()["message"] == "Verification email sent"
            mock_send.assert_called_once()

    def test_rejects_for_verified_user(self, client):
        user = UserFactory(is_verified=True)
        token = self._get_token(client, user)

        response = client.post(
            "/api/auth/resend-verification",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Email already verified"

    def test_rate_limits_requests(self, client):
        user = UserFactory(is_verified=False)
        token = self._get_token(client, user)

        # Create a recent verification code so the cooldown is active
        EmailVerificationCodeFactory(user=user)

        response = client.post(
            "/api/auth/resend-verification",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 400
        assert "wait" in response.json()["detail"].lower()

    def test_requires_authentication(self, client):
        response = client.post(
            "/api/auth/resend-verification",
            content_type="application/json",
        )

        assert response.status_code == 401

    def _get_token(self, client, user):
        return create_access_token(user.id)
