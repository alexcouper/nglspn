from datetime import datetime, timedelta
from uuid import UUID

from ninja import Schema


class DiscussionAuthor(Schema):
    id: UUID
    first_name: str
    last_name: str


class DiscussionCreate(Schema):
    body: str


def _resolve_author(obj: object) -> dict | None:
    author = getattr(obj, "author", None)
    if author is None:
        return None
    return {
        "id": author.id,
        "first_name": author.first_name,
        "last_name": author.last_name,
    }


def _resolve_is_edited(obj: object) -> bool:
    created_at = getattr(obj, "created_at", None)
    updated_at = getattr(obj, "updated_at", None)
    if created_at is None or updated_at is None:
        return False
    return updated_at > created_at + timedelta(seconds=1)


class ReplyResponse(Schema):
    id: UUID
    body: str
    created_at: datetime
    author: DiscussionAuthor | None
    is_edited: bool

    resolve_author = staticmethod(_resolve_author)
    resolve_is_edited = staticmethod(_resolve_is_edited)


class DiscussionResponse(Schema):
    id: UUID
    body: str
    created_at: datetime
    author: DiscussionAuthor | None
    is_edited: bool
    replies: list[ReplyResponse] = []

    resolve_author = staticmethod(_resolve_author)
    resolve_is_edited = staticmethod(_resolve_is_edited)

    @staticmethod
    def resolve_replies(obj: object) -> list:
        return list(obj.replies.all().order_by("created_at"))
