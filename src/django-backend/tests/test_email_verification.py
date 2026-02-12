from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from api.services.email import (
    VERIFICATION_CODE_EXPIRY_MINUTES,
    VERIFICATION_COOLDOWN_SECONDS,
    RateLimitError,
    create_verification_code,
    generate_verification_code,
    render_email,
    send_verification_email,
    verify_code,
)
from apps.users.models import EmailVerificationCode

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
class TestCreateVerificationCode:
    def test_creates_code_for_user(self):
        user = UserFactory()
        verification = create_verification_code(user)

        assert verification.user == user
        assert len(verification.code) == 6
        assert verification.expires_at > timezone.now()
        assert verification.used_at is None

    def test_code_expires_after_configured_minutes(self):
        user = UserFactory()
        before = timezone.now()
        verification = create_verification_code(user)
        after = timezone.now()

        expected_min = before + timedelta(minutes=VERIFICATION_CODE_EXPIRY_MINUTES)
        expected_max = after + timedelta(minutes=VERIFICATION_CODE_EXPIRY_MINUTES)

        assert expected_min <= verification.expires_at <= expected_max

    def test_rate_limits_requests(self):
        user = UserFactory()
        create_verification_code(user)

        with pytest.raises(RateLimitError):
            create_verification_code(user)

    def test_allows_new_code_after_cooldown(self):
        user = UserFactory()
        verification = create_verification_code(user)

        verification.created_at = timezone.now() - timedelta(
            seconds=VERIFICATION_COOLDOWN_SECONDS + 1
        )
        verification.save()

        new_verification = create_verification_code(user)
        assert new_verification.id != verification.id


@pytest.mark.django_db
class TestVerifyCode:
    def test_verifies_valid_code(self):
        user = UserFactory(is_verified=False)
        verification = EmailVerificationCodeFactory(user=user, code="123456")

        result = verify_code(user, "123456")

        assert result is True
        user.refresh_from_db()
        verification.refresh_from_db()
        assert user.is_verified is True
        assert verification.used_at is not None

    def test_rejects_invalid_code(self):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(user=user, code="123456")

        result = verify_code(user, "654321")

        assert result is False
        user.refresh_from_db()
        assert user.is_verified is False

    def test_rejects_expired_code(self):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(
            user=user,
            code="123456",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        result = verify_code(user, "123456")

        assert result is False
        user.refresh_from_db()
        assert user.is_verified is False

    def test_rejects_already_used_code(self):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(
            user=user,
            code="123456",
            used_at=timezone.now(),
        )

        result = verify_code(user, "123456")

        assert result is False
        user.refresh_from_db()
        assert user.is_verified is False


@pytest.mark.django_db
class TestRegistrationSendsVerificationEmail:
    def test_sends_email_on_registration(self, client):
        with patch("api.routers.auth.send_verification_email") as mock_send:
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

        with patch("api.routers.auth.send_verification_email"):
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

        with patch("api.routers.auth.send_verification_email") as mock_send:
            client.post(
                "/api/auth/login",
                data={"email": user.email, "password": "testpassword123"},
                content_type="application/json",
            )

            mock_send.assert_called_once()

    def test_does_not_send_email_for_verified_user(self, client):
        user = UserFactory(is_verified=True)

        with patch("api.routers.auth.send_verification_email") as mock_send:
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
        with patch("api.routers.auth.send_verification_email"):
            response = client.post(
                "/api/auth/login",
                data={"email": user.email, "password": "testpassword123"},
                content_type="application/json",
            )
        return response.json()["access_token"]


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

        with patch("api.routers.auth.send_verification_email") as mock_send:
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
        with patch("api.routers.auth.send_verification_email"):
            response = client.post(
                "/api/auth/login",
                data={"email": user.email, "password": "testpassword123"},
                content_type="application/json",
            )
        return response.json()["access_token"]


class TestRenderEmail:
    def test_renders_html_with_branding_colors(self):
        html, _ = render_email(
            "verification_code",
            {
                "code": "123456",
                "expiry_minutes": 15,
                "user_name": "Test",
                "logo_url": "https://example.com/logo.png",
                "current_year": 2025,
            },
        )

        assert "#ffffff" in html  # white background
        assert "Naglasúpan" in html  # brand name

    def test_renders_html_with_verification_code(self):
        html, _ = render_email(
            "verification_code",
            {
                "code": "987654",
                "expiry_minutes": 15,
                "user_name": "Test",
                "logo_url": "https://example.com/logo.png",
                "current_year": 2025,
            },
        )

        assert "987654" in html

    def test_renders_plain_text_fallback(self):
        _, text = render_email(
            "verification_code",
            {
                "code": "112233",
                "expiry_minutes": 15,
                "user_name": "Alice",
                "logo_url": "https://example.com/logo.png",
                "current_year": 2025,
            },
        )

        assert "112233" in text
        assert "Hi Alice" in text
        assert "15 minutes" in text


@pytest.mark.django_db
class TestSendVerificationEmailFormat:
    def test_sends_email_with_html_and_text_parts(self, mailoutbox):
        user = UserFactory(first_name="Bob")

        send_verification_email(user, "654321")

        assert len(mailoutbox) == 1
        email = mailoutbox[0]
        assert email.to == [user.email]
        assert email.subject == "Verify your email - Naglasúpan"
        assert "654321" in email.body  # plain text body
        assert len(email.alternatives) == 1
        html_content, mime_type = email.alternatives[0]
        assert mime_type == "text/html"
        assert "654321" in html_content
        assert "#ffffff" in html_content  # white background
