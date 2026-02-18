from __future__ import annotations

import secrets
from datetime import timedelta
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.users.models import EmailVerificationCode

from .exceptions import (
    EmailAlreadyRegisteredError,
    KennitalaAlreadyRegisteredError,
    RateLimitError,
    UserNotFoundError,
)
from .handler_interface import UserHandlerInterface
from .query_interface import UserQueryInterface

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.users.models import User

    from .handler_interface import RegisterUserInput


VERIFICATION_CODE_EXPIRY_MINUTES = 15
VERIFICATION_COOLDOWN_SECONDS = 60


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


class DjangoUserQuery(UserQueryInterface):
    def get_by_id(self, user_id: UUID) -> User:
        user_model = get_user_model()
        try:
            return user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            raise UserNotFoundError from None

    def get_active_by_id(self, user_id: UUID) -> User | None:
        user_model = get_user_model()
        try:
            user = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            return None
        return user if user.is_active else None

    def email_exists(self, email: str) -> bool:
        return get_user_model().objects.filter(email=email).exists()

    def kennitala_exists(self, kennitala: str) -> bool:
        return get_user_model().objects.filter(kennitala=kennitala).exists()

    def list_opted_in_for_broadcast_type(self, email_type: str) -> QuerySet:
        user_model = get_user_model()
        if email_type == "platform_updates":
            return user_model.objects.filter(
                email_opt_in_platform_updates=True,
                is_active=True,
            )
        if email_type == "competition_results":
            return user_model.objects.filter(
                email_opt_in_competition_results=True,
                is_active=True,
            )
        return user_model.objects.none()


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
