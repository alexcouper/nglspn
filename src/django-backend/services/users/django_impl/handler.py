from __future__ import annotations

import secrets
from datetime import timedelta
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.users.models import EmailVerificationCode, PasswordResetCode
from services.users.exceptions import (
    CodeExhaustedError,
    EmailAlreadyRegisteredError,
    KennitalaAlreadyRegisteredError,
    RateLimitError,
)
from services.users.handler_interface import UserHandlerInterface, VerifyResetCodeResult

if TYPE_CHECKING:
    from apps.users.models import User
    from services.users.handler_interface import RegisterUserInput


VERIFICATION_COOLDOWN_SECONDS = 60
PASSWORD_RESET_MAX_ATTEMPTS = 3


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


class DjangoUserHandler(UserHandlerInterface):
    def register(self, data: RegisterUserInput) -> User:
        user_model = get_user_model()

        if user_model.objects.filter(email=data.email).exists():
            raise EmailAlreadyRegisteredError

        if user_model.objects.filter(kennitala=data.kennitala).exists():
            raise KennitalaAlreadyRegisteredError

        return user_model.objects.create_user(
            email=data.email,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name,
            kennitala=data.kennitala,
        )

    def create_verification_code(
        self, user: User, expires_minutes: int
    ) -> EmailVerificationCode:
        now = timezone.now()
        cooldown_threshold = now - timedelta(seconds=VERIFICATION_COOLDOWN_SECONDS)

        recent_code = EmailVerificationCode.objects.filter(
            user=user,
            created_at__gte=cooldown_threshold,
        ).first()

        if recent_code:
            raise RateLimitError

        code = generate_verification_code()
        expires_at = now + timedelta(minutes=expires_minutes)

        return EmailVerificationCode.objects.create(
            user=user,
            code=code,
            expires_at=expires_at,
        )

    def verify_code(self, user: User, code: str) -> bool:
        now = timezone.now()

        verification = EmailVerificationCode.objects.filter(
            user=user,
            code=code,
            expires_at__gt=now,
            used_at__isnull=True,
        ).first()

        if not verification:
            return False

        verification.used_at = now
        verification.save(update_fields=["used_at"])

        user.is_verified = True
        user.save(update_fields=["is_verified"])

        return True

    def create_password_reset_code(
        self, email: str, expires_minutes: int
    ) -> PasswordResetCode | None:
        user_model = get_user_model()

        try:
            user = user_model.objects.get(email=email)
        except user_model.DoesNotExist:
            return None

        now = timezone.now()
        cooldown_threshold = now - timedelta(seconds=VERIFICATION_COOLDOWN_SECONDS)

        recent_code = PasswordResetCode.objects.filter(
            user=user,
            created_at__gte=cooldown_threshold,
        ).first()

        if recent_code:
            raise RateLimitError

        code = generate_verification_code()
        expires_at = now + timedelta(minutes=expires_minutes)

        return PasswordResetCode.objects.create(
            user=user,
            code=code,
            expires_at=expires_at,
        )

    def verify_password_reset_code(
        self, email: str, code: str
    ) -> VerifyResetCodeResult:
        user_model = get_user_model()

        try:
            user = user_model.objects.get(email=email)
        except user_model.DoesNotExist:
            return VerifyResetCodeResult(user=None, attempts_remaining=0)

        now = timezone.now()

        reset_code = (
            PasswordResetCode.objects.filter(
                user=user,
                expires_at__gt=now,
                used_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )

        if not reset_code:
            return VerifyResetCodeResult(user=None, attempts_remaining=0)

        if reset_code.attempts >= PASSWORD_RESET_MAX_ATTEMPTS:
            raise CodeExhaustedError

        if reset_code.code != code:
            reset_code.attempts += 1
            reset_code.save(update_fields=["attempts"])
            remaining = PASSWORD_RESET_MAX_ATTEMPTS - reset_code.attempts
            if remaining <= 0:
                raise CodeExhaustedError
            return VerifyResetCodeResult(user=None, attempts_remaining=remaining)

        reset_code.used_at = now
        reset_code.save(update_fields=["used_at"])

        return VerifyResetCodeResult(
            user=user,
            attempts_remaining=PASSWORD_RESET_MAX_ATTEMPTS - reset_code.attempts,
        )

    def reset_password(self, user: User, new_password: str) -> None:
        user.set_password(new_password)
        user.save(update_fields=["password"])
