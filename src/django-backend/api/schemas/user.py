from datetime import datetime
from typing import Any, Literal
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
    # Resolved off `User.avatar_url`: null until an upload has completed.
    avatar_url: str | None = None
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
    """What anyone may know about a user.

    Embedded in every project (creator, contributors) and article (author), so
    everything here must come off the user row and its `avatar` FK — the list
    querysets `select_related` that FK for exactly this reason. The person's
    projects and articles are separate endpoints, never fields here.
    """

    id: UUID
    first_name: str
    last_name: str
    info: str
    is_system_user: bool = False
    avatar_url: str | None = None
    created_at: datetime


class AvatarUploadRequest(Schema):
    filename: str
    content_type: str
    file_size: int


class UserProjectResponse(Schema):
    """One entry in a user's public project list.

    `role` is the contributor row's role. `full_edit` is deliberately absent:
    it is an editing permission, not a public fact.
    """

    id: UUID
    slug: str | None
    title: str
    tagline: str
    category_name: str | None
    main_image_thumb_url: str | None
    role: Literal["owner", "tipster"]

    @classmethod
    def from_item(cls, item: Any) -> "UserProjectResponse":
        return cls(
            id=item.project.id,
            slug=item.project.slug,
            title=item.project.title,
            tagline=item.project.tagline,
            category_name=item.category_name,
            main_image_thumb_url=item.main_image_thumb_url,
            role=item.role,
        )
