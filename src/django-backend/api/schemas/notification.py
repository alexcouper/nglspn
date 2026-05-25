from datetime import datetime
from uuid import UUID

from ninja import Schema
from pydantic import model_validator

from services.notifications import (
    NotificationGroup,
    NotificationGroupKind,
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
    kind: NotificationGroupKind
    project: NotificationProjectResponse
    latest_body_excerpt: str
    latest_event_at: datetime
    unread_count: int
    # Discussion-specific (null for article groups)
    root_discussion_id: UUID | None = None
    headline_kind: NotificationHeadlineKind | None = None
    actor_names: list[str] = []
    latest_comment_id: UUID | None = None
    # Article-specific (null for discussion groups)
    article_id: UUID | None = None
    article_slug: str | None = None
    article_title: str | None = None
    channel_name: str | None = None

    @classmethod
    def from_dataclass(cls, group: NotificationGroup) -> "NotificationGroupResponse":
        return cls(
            kind=group.kind,
            project=NotificationProjectResponse(
                id=group.project.id,
                slug=group.project.slug,
                title=group.project.title,
                image_url=group.project.image_url,
            ),
            latest_body_excerpt=group.latest_body_excerpt,
            latest_event_at=group.latest_event_at,
            unread_count=group.unread_count,
            root_discussion_id=group.root_discussion_id,
            headline_kind=group.headline_kind,
            actor_names=list(group.actor_names),
            latest_comment_id=group.latest_comment_id,
            article_id=group.article_id,
            article_slug=group.article_slug,
            article_title=group.article_title,
            channel_name=group.channel_name,
        )


class MarkThreadReadRequest(Schema):
    root_discussion_id: UUID | None = None
    comment_id: UUID | None = None
    article_id: UUID | None = None

    @model_validator(mode="after")
    def exactly_one(self) -> "MarkThreadReadRequest":
        provided = sum(
            x is not None
            for x in (self.root_discussion_id, self.comment_id, self.article_id)
        )
        if provided != 1:
            msg = (
                "exactly one of root_discussion_id, comment_id or article_id"
                " is required"
            )
            raise ValueError(msg)
        return self


class MarkThreadReadResponse(Schema):
    marked: int


class MarkAllReadResponse(Schema):
    marked: int
