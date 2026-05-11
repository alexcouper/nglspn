from datetime import datetime
from uuid import UUID

from ninja import Schema

from services.notifications import (
    NotificationGroup,
    NotificationHeadlineKind,
    NotificationSummary,
)


class NotificationSummaryResponse(Schema):
    has_unread: bool
    unread_group_count: int

    @classmethod
    def from_dataclass(
        cls, summary: NotificationSummary
    ) -> "NotificationSummaryResponse":
        return cls(
            has_unread=summary.has_unread,
            unread_group_count=summary.unread_group_count,
        )


class NotificationProjectResponse(Schema):
    id: UUID
    slug: str | None
    title: str
    image_url: str | None


class NotificationGroupResponse(Schema):
    root_discussion_id: UUID
    project: NotificationProjectResponse
    headline_kind: NotificationHeadlineKind
    actor_names: list[str]
    latest_body_excerpt: str
    latest_event_at: datetime
    unread_count: int
    latest_comment_id: UUID

    @classmethod
    def from_dataclass(cls, group: NotificationGroup) -> "NotificationGroupResponse":
        return cls(
            root_discussion_id=group.root_discussion_id,
            project=NotificationProjectResponse(
                id=group.project.id,
                slug=group.project.slug,
                title=group.project.title,
                image_url=group.project.image_url,
            ),
            headline_kind=group.headline_kind,
            actor_names=group.actor_names,
            latest_body_excerpt=group.latest_body_excerpt,
            latest_event_at=group.latest_event_at,
            unread_count=group.unread_count,
            latest_comment_id=group.latest_comment_id,
        )


class MarkThreadReadRequest(Schema):
    root_discussion_id: UUID


class MarkThreadReadResponse(Schema):
    marked: int


class MarkAllReadResponse(Schema):
    marked: int
