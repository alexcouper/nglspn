from datetime import datetime
from uuid import UUID

from ninja import Schema


class FollowStateResponse(Schema):
    is_followed: bool
    created_at: datetime | None = None


class FollowChannelPreferenceResponse(Schema):
    channel_id: UUID
    channel_name: str
    email_enabled: bool
    in_app_enabled: bool


class FollowResponse(Schema):
    project_slug: str
    project_title: str
    project_hero_image_url: str | None = None
    created_at: datetime
    channels: list[FollowChannelPreferenceResponse]


class FollowChannelPreferencePatch(Schema):
    email_enabled: bool | None = None
    in_app_enabled: bool | None = None
