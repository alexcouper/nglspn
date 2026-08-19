from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from apps.articles.models import Article
    from apps.discussions.models import Discussion
    from apps.feed.models import FeedEvent
    from apps.projects.models import Competition, Project


class FeedHandlerInterface(ABC):
    """Writes to the append-only feed stream.

    Every append is idempotent on its (kind, subject) pair, so a source firing
    twice — or the backfill running again — adds nothing.
    """

    @abstractmethod
    def append_article_published(self, article: Article) -> FeedEvent | None: ...

    @abstractmethod
    def append_project_published(self, project: Project) -> FeedEvent | None: ...

    @abstractmethod
    def append_competition_opened(
        self, competition: Competition
    ) -> FeedEvent | None: ...

    @abstractmethod
    def append_competition_closed(
        self, competition: Competition
    ) -> FeedEvent | None: ...

    @abstractmethod
    def append_competition_winner(
        self, competition: Competition
    ) -> FeedEvent | None: ...

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

    @abstractmethod
    def link_article_to_event(
        self,
        article: Article,
        event_id: UUID | None,
    ) -> FeedEvent | None:
        """Point an article's own event at the event it supersedes.

        Returns the superseded event, or None when nothing was superseded —
        either because no target was given, or because the target had already
        been superseded once. Superseding is one-shot by design.
        """
