from uuid import UUID

from ninja import Schema


class ChannelCreate(Schema):
    name: str


class ChannelRename(Schema):
    name: str


class ChannelReassign(Schema):
    target_channel_id: UUID


class ChannelResponse(Schema):
    id: UUID
    name: str


class ChannelReassignResponse(Schema):
    reassigned: int


class ChannelConflictResponse(Schema):
    detail: str
    article_count: int | None = None
