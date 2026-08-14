from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.feed.models import FeedEvent, FeedEventKind
from services.feed.query_interface import FeedQueryInterface

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.articles.models import Article

MAX_PAGE_SIZE = 50
SUGGESTION_LIMIT = 10


class DjangoFeedQuery(FeedQueryInterface):
    def get_by_id(self, event_id: UUID) -> FeedEvent | None:
        return FeedEvent.objects.with_sources().filter(pk=event_id).first()

    def renderable(self) -> QuerySet[FeedEvent]:
        return FeedEvent.objects.renderable().with_sources()

    def page(
        self,
        *,
        before: datetime | None = None,
        limit: int = 20,
    ) -> list[FeedEvent]:
        qs = self.renderable()
        if before is not None:
            qs = qs.filter(occurred_at__lt=before)
        return list(qs[: min(limit, MAX_PAGE_SIZE)])

    def lead(self, *, freshness_days: int) -> FeedEvent | None:
        pinned = self.renderable().filter(is_pinned=True).first()
        if pinned is not None:
            return pinned

        newest = self.renderable().first()
        if newest is None or newest.article_id is None:
            # A bare event never leads — only a write-up earns the space.
            return None

        cutoff = timezone.now() - timedelta(days=freshness_days)
        if newest.occurred_at < cutoff:
            return None
        return newest

    def live_event_for_article(self, article_id: UUID) -> FeedEvent | None:
        return FeedEvent.objects.renderable().filter(article_id=article_id).first()

    def suggest_events_for_article(self, article: Article) -> list[FeedEvent]:
        candidates = list(
            FeedEvent.objects.renderable()
            .with_sources()
            .filter(kind=FeedEventKind.COMPETITION_WINNER)[:SUGGESTION_LIMIT]
        )
        # Naming the competition is the strongest signal an author gives us, so
        # a title match outranks recency. Everything else stays in stream order.
        title = (article.title or "").casefold()
        named = [
            event
            for event in candidates
            if event.competition and event.competition.name.casefold() in title
        ]
        rest = [event for event in candidates if event not in named]
        return named + rest
