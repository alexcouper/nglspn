from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.feed.models import FeedEvent


class FeedQueryInterface(ABC):
    @abstractmethod
    def get_by_id(self, event_id: UUID) -> FeedEvent | None: ...

    @abstractmethod
    def page(
        self,
        *,
        before: datetime | None = None,
        limit: int = 20,
    ) -> list[FeedEvent]:
        """Renderable events, newest first, starting strictly before `before`.

        The cursor is `occurred_at`, which never changes once written, so a
        reader paging through sees every entry exactly once.
        """

    @abstractmethod
    def lead(self, *, freshness_days: int) -> FeedEvent | None:
        """The entry to render full width, or None to start the feed flat.

        A pinned entry wins. Otherwise the newest renderable entry qualifies
        only when it carries an article published inside the window.
        """

    @abstractmethod
    def renderable(self) -> QuerySet[FeedEvent]: ...

    @abstractmethod
    def live_event_for_article(self, article_id: UUID) -> FeedEvent | None: ...
