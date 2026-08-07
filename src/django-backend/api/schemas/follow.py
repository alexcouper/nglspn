from datetime import datetime
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
    project_slug: str
    project_title: str
    project_hero_image_url: str | None = None
    created_at: datetime
    channels: list[ChannelFollowStateResponse]
