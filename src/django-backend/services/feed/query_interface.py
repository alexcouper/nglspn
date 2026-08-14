from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.feed.models import FeedEvent
    from services.feed.cursor import FeedCursor


class FeedQueryInterface(ABC):
    @abstractmethod
    def get_by_id(self, event_id: UUID) -> FeedEvent | None: ...

    @abstractmethod
    def page(
        self,
        *,
        before: FeedCursor | None = None,
        limit: int = 20,
    ) -> list[FeedEvent]:
        """Renderable events, newest first, starting strictly after `before`.

        The cursor is `(occurred_at, created_at)`, neither of which changes once
        written, so a reader paging through sees every entry exactly once — and
        entries sharing an `occurred_at` are not lost at the page boundary.

        A pinned entry is left out: it renders as the lead, and paging it in as
        well would show it twice on the page it happens to fall on.
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
