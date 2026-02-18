from __future__ import annotations

import secrets
from datetime import timedelta
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.users.models import EmailVerificationCode
from svc.users.exceptions import (
    EmailAlreadyRegisteredError,
    KennitalaAlreadyRegisteredError,
    RateLimitError,
)
from svc.users.handler_interface import UserHandlerInterface

if TYPE_CHECKING:
    from apps.users.models import User
    from svc.users.handler_interface import RegisterUserInput


VERIFICATION_CODE_EXPIRY_MINUTES = 15
VERIFICATION_COOLDOWN_SECONDS = 60


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

    def create_verification_code(self, user: User) -> EmailVerificationCode:
        now = timezone.now()
        cooldown_threshold = now - timedelta(seconds=VERIFICATION_COOLDOWN_SECONDS)

        recent_code = EmailVerificationCode.objects.filter(
            user=user,
            created_at__gte=cooldown_threshold,
        ).first()

        if recent_code:
            raise RateLimitError

        code = generate_verification_code()
        expires_at = now + timedelta(minutes=VERIFICATION_CODE_EXPIRY_MINUTES)

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
