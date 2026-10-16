from datetime import datetime
from typing import Literal
from uuid import UUID

from ninja import Schema


class FollowStateResponse(Schema):
    is_followed: bool
    created_at: datetime | None = None


class ChannelFollowStateResponse(Schema):
    channel_id: UUID
    channel_name: str
    followed: bool


class FollowResponse(Schema):
    """A followed project or a followed person; `target` says which and the
    other side's fields are null."""

    target: Literal["project", "user"]
    project_slug: str | None = None
    project_title: str | None = None
    project_hero_image_url: str | None = None
    user_id: UUID | None = None
    user_name: str | None = None
    user_avatar_url: str | None = None
    created_at: datetime
    channels: list[ChannelFollowStateResponse]
