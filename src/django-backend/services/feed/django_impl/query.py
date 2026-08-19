from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.db.models import Q
from django.utils import timezone

from apps.feed.models import FeedEvent
from services.feed.query_interface import FeedQueryInterface

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from services.feed.cursor import FeedCursor

# The largest page the read API will serve. Declared here rather than in the
# router because the cap has to be enforced where the rows are fetched; the
# router imports it so there is one number.
MAX_PAGE_SIZE = 50

# Callers detect a further page by asking for one row beyond the page they will
# serve. Clamping at MAX_PAGE_SIZE would eat that row at the largest page size,
# and the caller would read "no extra row" as "stream exhausted" and stop paging
# with entries still to come.
FETCH_CEILING = MAX_PAGE_SIZE + 1


class DjangoFeedQuery(FeedQueryInterface):
    def _renderable(self) -> QuerySet[FeedEvent]:
        """Private: a Django QuerySet is not something the interface hands out."""
        return FeedEvent.objects.renderable().with_sources()

    def page(
        self,
        *,
        before: FeedCursor | None = None,
        limit: int = 20,
    ) -> list[FeedEvent]:
        # The pinned entry is the lead. Excluding it here rather than in the
        # router is what keeps it out of *every* page: the router only sees the
        # lead on the first request, but a pinned entry can sit anywhere in the
        # stream.
        qs = self._renderable().exclude(is_pinned=True)
        if before is not None:
            # Ordering is (-occurred_at, -created_at); the boundary comparison
            # has to match it, or rows tied on occurred_at fall through the gap.
            qs = qs.filter(
                Q(occurred_at__lt=before.occurred_at)
                | Q(
                    occurred_at=before.occurred_at,
                    created_at__lt=before.created_at,
                )
            )
        return list(qs[: min(limit, FETCH_CEILING)])

    def lead(self, *, freshness_days: int) -> FeedEvent | None:
        pinned = self._renderable().filter(is_pinned=True).first()
        if pinned is not None:
            return pinned

        newest = self._renderable().first()
        if newest is None or newest.article_id is None:
            # A bare event never leads — only a write-up earns the space.
            return None

        cutoff = timezone.now() - timedelta(days=freshness_days)
        if newest.occurred_at < cutoff:
            return None
        return newest
