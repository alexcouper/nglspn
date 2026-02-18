import pytest
from django.utils import timezone

from svc.users.django_impl import DjangoUserHandler
from svc.users.exceptions import (
    EmailAlreadyRegisteredError,
    KennitalaAlreadyRegisteredError,
)
from svc.users.handler_interface import RegisterUserInput
from tests.factories import EmailVerificationCodeFactory, UserFactory

handler = DjangoUserHandler()


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

        verification = handler.create_verification_code(user)

        assert verification.user == user
        assert len(verification.code) == 6
        assert verification.code.isdigit()
        assert verification.expires_at > timezone.now()


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
