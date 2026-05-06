from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class NotificationProject:
    id: UUID
    slug: str | None
    title: str
    image_url: str | None


@dataclass(frozen=True)
class NotificationGroup:
    root_discussion_id: UUID
    project: NotificationProject
    headline_kind: str
    actor_names: list[str]
    latest_body_excerpt: str
    latest_event_at: datetime
    unread_count: int
    latest_comment_id: UUID


@dataclass(frozen=True)
class NotificationSummary:
    has_unread: bool
    unread_group_count: int


__all__ = [
    "NotificationGroup",
    "NotificationProject",
    "NotificationSummary",
]
