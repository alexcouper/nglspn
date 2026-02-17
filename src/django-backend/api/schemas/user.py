from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema


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
    kennitala: str | None
    info: str
    is_verified: bool
    created_at: datetime
    groups: list[str]
    email_opt_in_competition_results: bool
    email_opt_in_platform_updates: bool
    opt_in_to_external_promotions: bool

    @staticmethod
    def resolve_groups(obj: Any) -> list[str]:
        return list(obj.groups.values_list("name", flat=True))


class UserUpdate(Schema):
    first_name: str | None = None
    last_name: str | None = None
    info: str | None = None
    email_opt_in_competition_results: bool | None = None
    email_opt_in_platform_updates: bool | None = None
    opt_in_to_external_promotions: bool | None = None


class PublicUserProfile(Schema):
    id: UUID
    first_name: str
    last_name: str
    info: str
