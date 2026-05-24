from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class NotificationHeadlineKind(str, Enum):
    STARTED = "started"
    REPLIED = "replied"


class NotificationGroupKind(str, Enum):
    DISCUSSION = "discussion"
    ARTICLE = "article"


@dataclass(frozen=True)
class NotificationProject:
    id: UUID
    slug: str | None
    title: str
    image_url: str | None


@dataclass(frozen=True)
class NotificationGroup:
    kind: NotificationGroupKind
    project: NotificationProject
    latest_event_at: datetime
    unread_count: int
    latest_body_excerpt: str
    # Discussion-specific fields (None for article groups)
    root_discussion_id: UUID | None = None
    headline_kind: NotificationHeadlineKind | None = None
    actor_names: list[str] = field(default_factory=list)
    latest_comment_id: UUID | None = None
    # Article-specific fields (None for discussion groups)
    article_id: UUID | None = None
    article_slug: str | None = None
    article_title: str | None = None
    channel_name: str | None = None


@dataclass(frozen=True)
class NotificationSummary:
    has_unread: bool
    unread_group_count: int


__all__ = [
    "NotificationGroup",
    "NotificationGroupKind",
    "NotificationHeadlineKind",
    "NotificationProject",
    "NotificationSummary",
]
