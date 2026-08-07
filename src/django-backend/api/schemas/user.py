from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema

from apps.users.models import ArticleEmailFrequency, DiscussionEmailFrequency


class UserCreate(Schema):
    email: str
    password: str
    kennitala: str
    first_name: str = ""
    last_name: str = ""


class UserResponse(Schema):
    id: UUID
    email: str
    first_name: str
    last_name: str
    info: str
    is_verified: bool
    is_system_user: bool = False
    created_at: datetime
    groups: list[str]
    opt_in_to_external_promotions: bool
    discussion_email_frequency: str
    article_email_frequency: str
    pending_onboarding_steps: list[str]

    @staticmethod
    def resolve_groups(obj: Any) -> list[str]:
        return list(obj.groups.values_list("name", flat=True))

    @staticmethod
    def resolve_pending_onboarding_steps(obj: Any) -> list[str]:
        from services import HANDLERS  # noqa: PLC0415

        return [step.id for step in HANDLERS.registration.get_pending_steps(obj)]


class UserUpdate(Schema):
    first_name: str | None = None
    last_name: str | None = None
    info: str | None = None
    opt_in_to_external_promotions: bool | None = None
    discussion_email_frequency: DiscussionEmailFrequency | None = None
    article_email_frequency: ArticleEmailFrequency | None = None


class PublicUserProfile(Schema):
    id: UUID
    first_name: str
    last_name: str
    info: str
    is_system_user: bool = False
