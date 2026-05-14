from datetime import datetime

from ninja import Schema


class FollowStateResponse(Schema):
    is_followed: bool
    created_at: datetime | None = None
