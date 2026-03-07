from datetime import datetime
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


class ReplyResponse(Schema):
    id: UUID
    body: str
    created_at: datetime
    author: DiscussionAuthor | None

    resolve_author = staticmethod(_resolve_author)


class DiscussionResponse(Schema):
    id: UUID
    body: str
    created_at: datetime
    author: DiscussionAuthor | None
    replies: list[ReplyResponse] = []

    resolve_author = staticmethod(_resolve_author)

    @staticmethod
    def resolve_replies(obj: object) -> list:
        return list(obj.replies.all().order_by("created_at"))
