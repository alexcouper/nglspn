from datetime import timedelta

import pytest
from django.utils import timezone

from svc.users.django_impl import (
    VERIFICATION_COOLDOWN_SECONDS,
    DjangoUserHandler,
    generate_verification_code,
)
from svc.users.exceptions import (
    EmailAlreadyRegisteredError,
    KennitalaAlreadyRegisteredError,
    RateLimitError,
)
from svc.users.handler_interface import RegisterUserInput
from tests.factories import EmailVerificationCodeFactory, UserFactory

handler = DjangoUserHandler()


class TestGenerateVerificationCode:
    def test_generates_6_digit_code(self):
        code = generate_verification_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_generates_different_codes(self):
        codes = {generate_verification_code() for _ in range(100)}
        assert len(codes) > 1


@pytest.mark.django_db
class TestRegister:
    def test_creates_user_with_correct_fields(self):
        data = RegisterUserInput(
            email="new@example.com",
            password="securepass123",
            kennitala="1234567890",
            first_name="Jane",
            last_name="Doe",
        )

        user = handler.register(data)

        assert user.email == "new@example.com"
        assert user.first_name == "Jane"
        assert user.last_name == "Doe"
        assert user.kennitala == "1234567890"
        assert user.check_password("securepass123")

    def test_raises_on_duplicate_email(self):
        UserFactory(email="taken@example.com")
        data = RegisterUserInput(
            email="taken@example.com",
            password="pass123",
            kennitala="9999999999",
            first_name="A",
            last_name="B",
        )

        with pytest.raises(EmailAlreadyRegisteredError):
            handler.register(data)

    def test_raises_on_duplicate_kennitala(self):
        UserFactory(kennitala="1111111111")
        data = RegisterUserInput(
            email="unique@example.com",
            password="pass123",
            kennitala="1111111111",
            first_name="A",
            last_name="B",
        )

        with pytest.raises(KennitalaAlreadyRegisteredError):
            handler.register(data)


@pytest.mark.django_db
class TestCreateVerificationCode:
    def test_creates_code_for_user(self):
        user = UserFactory()

        verification = handler.create_verification_code(user, expires_minutes=15)

        assert verification.user == user
        assert len(verification.code) == 6
        assert verification.code.isdigit()
        assert verification.expires_at > timezone.now()

    def test_code_expires_after_configured_minutes(self):
        user = UserFactory()
        before = timezone.now()
        verification = handler.create_verification_code(user, expires_minutes=5)
        after = timezone.now()

        expected_min = before + timedelta(minutes=5)
        expected_max = after + timedelta(minutes=5)
        assert expected_min <= verification.expires_at <= expected_max

    def test_rate_limits_requests(self):
        user = UserFactory()
        handler.create_verification_code(user, expires_minutes=15)

        with pytest.raises(RateLimitError):
            handler.create_verification_code(user, expires_minutes=15)

    def test_allows_new_code_after_cooldown(self):
        user = UserFactory()
        verification = handler.create_verification_code(user, expires_minutes=15)

        verification.created_at = timezone.now() - timedelta(
            seconds=VERIFICATION_COOLDOWN_SECONDS + 1
        )
        verification.save()

        new_verification = handler.create_verification_code(user, expires_minutes=15)
        assert new_verification.id != verification.id


@pytest.mark.django_db
class TestVerifyCode:
    def test_verifies_valid_code_and_marks_user_verified(self):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(user=user, code="123456")

        result = handler.verify_code(user, "123456")

        assert result is True
        user.refresh_from_db()
        assert user.is_verified is True

    def test_rejects_wrong_code(self):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(user=user, code="123456")

        result = handler.verify_code(user, "000000")

        assert result is False
        user.refresh_from_db()
        assert user.is_verified is False

    def test_verifies_valid_code(self):
        user = UserFactory(is_verified=False)
        verification = EmailVerificationCodeFactory(user=user, code="123456")

        result = handler.verify_code(user, "123456")

        assert result is True
        user.refresh_from_db()
        verification.refresh_from_db()
        assert user.is_verified is True
        assert verification.used_at is not None

    def test_rejects_invalid_code(self):
        user = UserFactory(is_verified=False)
        EmailVerificationCodeFactory(user=user, code="123456")

        result = handler.verify_code(user, "654321")

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

        result = handler.verify_code(user, "123456")

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

        result = handler.verify_code(user, "123456")

        assert result is False
        user.refresh_from_db()
        assert user.is_verified is False
