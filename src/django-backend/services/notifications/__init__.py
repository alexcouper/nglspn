from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class NotificationHeadlineKind(str, Enum):
    STARTED = "started"
    REPLIED = "replied"


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
    headline_kind: NotificationHeadlineKind
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
    "NotificationHeadlineKind",
    "NotificationProject",
    "NotificationSummary",
]
