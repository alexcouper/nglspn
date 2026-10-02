from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.feed.models import FeedEvent, FeedEventKind
from apps.projects.models import ProjectStatus
from services.feed.exceptions import FeedEventNotFoundError
from services.feed.handler_interface import FeedHandlerInterface

if TYPE_CHECKING:
    import datetime
    from uuid import UUID

    from apps.articles.models import Article
    from apps.discussions.models import Discussion
    from apps.projects.models import Project


def as_datetime(value: datetime.datetime | str | None) -> datetime.datetime:
    """The aware datetime an entry is ordered by.

    Strings are accepted because a field assigned a literal has not been coerced
    by the time post_save fires — the instance still holds what the caller set,
    so appending straight from it would see `"2026-01-15T09:00:00Z"`.
    """
    if isinstance(value, str):
        value = parse_datetime(value)
    if value is None:
        return timezone.now()
    return value if timezone.is_aware(value) else timezone.make_aware(value)


class DjangoFeedHandler(FeedHandlerInterface):
    def append_article_published(self, article: Article) -> FeedEvent | None:
        return self._append(
            FeedEventKind.ARTICLE_PUBLISHED,
            occurred_at=as_datetime(article.published_at),
            article=article,
        )

    def append_project_published(self, project: Project) -> FeedEvent | None:
        """A project enters the feed when it becomes visible, not when submitted.

        `published_at` marks submission for review; `approved_at` is when the
        site actually shows it. Discover already orders arrivals by
        `Coalesce(approved_at, created_at)` and the feed matches it, so the two
        surfaces agree about when something turned up.
        """
        if project.status != ProjectStatus.APPROVED:
            return None
        kind = (
            FeedEventKind.PROJECT_TIPOFF
            if project.is_community_tipoff
            else FeedEventKind.PROJECT_PUBLISHED
        )
        return self._append(
            kind,
            occurred_at=as_datetime(project.approved_at or project.created_at),
            project=project,
        )

    def promote_discussion(
        self,
        discussion: Discussion,
        *,
        occurred_at: datetime.datetime | None = None,
    ) -> FeedEvent | None:
        existing = FeedEvent.objects.filter(discussion=discussion).first()
        if existing is not None:
            # Promoting a previously retired thread brings it back rather than
            # colliding with the row that is already there.
            if existing.retired_at is not None:
                existing.retired_at = None
                existing.save(update_fields=["retired_at"])
            return existing
        return self._append(
            FeedEventKind.DISCUSSION_PROMOTED,
            occurred_at=occurred_at or timezone.now(),
            discussion=discussion,
        )

    def retire(self, event_id: UUID) -> FeedEvent:
        event = self._get(event_id)
        if event.retired_at is None:
            event.retired_at = timezone.now()
            event.save(update_fields=["retired_at"])
        return event

    def unretire(self, event_id: UUID) -> FeedEvent:
        event = self._get(event_id)
        if event.retired_at is not None:
            event.retired_at = None
            event.save(update_fields=["retired_at"])
        return event

    def set_pinned(self, event_id: UUID, *, pinned: bool) -> FeedEvent:
        event = self._get(event_id)
        with transaction.atomic():
            if pinned:
                # One lead at a time — pinning a second entry replaces the first
                # rather than leaving the choice to ordering.
                FeedEvent.objects.filter(is_pinned=True).exclude(pk=event.pk).update(
                    is_pinned=False
                )
            if event.is_pinned != pinned:
                event.is_pinned = pinned
                event.save(update_fields=["is_pinned"])
        return event

    def _append(
        self,
        kind: str,
        *,
        occurred_at: datetime.datetime,
        **subject,
    ) -> FeedEvent | None:
        """Append, or return the row that is already there.

        The unique constraints are the real guard; catching IntegrityError
        rather than checking first keeps concurrent appends safe.
        """
        existing = FeedEvent.objects.filter(**subject).first()
        if existing is not None:
            return existing
        try:
            with transaction.atomic():
                return FeedEvent.objects.create(
                    kind=kind, occurred_at=occurred_at, **subject
                )
        except IntegrityError:
            return FeedEvent.objects.filter(**subject).first()

    @staticmethod
    def _get(event_id: UUID) -> FeedEvent:
        event = FeedEvent.objects.filter(pk=event_id).first()
        if event is None:
            raise FeedEventNotFoundError(event_id)
        return event
