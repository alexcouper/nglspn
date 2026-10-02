from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from apps.articles.models import Article
    from apps.discussions.models import Discussion
    from apps.feed.models import FeedEvent
    from apps.projects.models import Project


class FeedHandlerInterface(ABC):
    """Writes to the append-only feed stream.

    Every append is idempotent on its subject, so a source firing twice — or
    the backfill running again — adds nothing.
    """

    @abstractmethod
    def append_article_published(self, article: Article) -> FeedEvent | None: ...

    @abstractmethod
    def append_project_published(self, project: Project) -> FeedEvent | None: ...

    @abstractmethod
    def promote_discussion(
        self,
        discussion: Discussion,
        *,
        occurred_at: datetime | None = None,
    ) -> FeedEvent | None: ...

    @abstractmethod
    def retire(self, event_id: UUID) -> FeedEvent: ...

    @abstractmethod
    def unretire(self, event_id: UUID) -> FeedEvent: ...

    @abstractmethod
    def set_pinned(self, event_id: UUID, *, pinned: bool) -> FeedEvent: ...
