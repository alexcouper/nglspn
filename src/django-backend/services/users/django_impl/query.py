from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

from services.users.exceptions import UserNotFoundError
from services.users.query_interface import UserQueryInterface

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.users.models import User


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
