from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

from apps.projects.models import Project
from apps.users.seed import COMMUNITY_USER_ID
from services.users.exceptions import UserNotFoundError
from services.users.query_interface import UserQueryInterface

# Maps a BroadcastEmail.email_type to the house-project channel whose
# per-user email preference now governs that broadcast. Replaces the legacy
# User.email_opt_in_* flags (dropped in add-article-authoring §9).
BROADCAST_CHANNEL_BY_EMAIL_TYPE = {
    "competition_results": "Competition Winners",
    "platform_updates": "Product Updates",
}

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
        if not user.is_active or user.is_system_user:
            return None
        return user

    def email_exists(self, email: str) -> bool:
        return get_user_model().objects.filter(email=email).exists()

    def kennitala_exists(self, kennitala: str) -> bool:
        return get_user_model().objects.filter(kennitala=kennitala).exists()

    def list_opted_in_for_broadcast_type(self, email_type: str) -> QuerySet:
        user_model = get_user_model()
        channel_name = BROADCAST_CHANNEL_BY_EMAIL_TYPE.get(email_type)
        if channel_name is None:
            return user_model.objects.none()
        house = Project.objects.filter(is_house_project=True).first()
        if house is None:
            return user_model.objects.none()
        return user_model.objects.filter(
            is_active=True,
            is_system_user=False,
            follows__project=house,
            follows__preferences__channel__name=channel_name,
            follows__preferences__email_enabled=True,
        ).distinct()

    def get_community_user(self) -> User:
        user_model = get_user_model()
        try:
            return user_model.objects.get(id=COMMUNITY_USER_ID)
        except user_model.DoesNotExist as exc:
            msg = (
                "Community/Unowned seed user not found. The seed migration may "
                "not have run."
            )
            raise RuntimeError(msg) from exc
