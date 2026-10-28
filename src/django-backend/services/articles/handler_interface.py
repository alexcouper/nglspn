from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from apps.articles.models import Article
    from apps.follows.models import Channel


class UnsetType:
    """Distinguishes 'field omitted' from 'field explicitly set to null'.

    PATCH payloads cannot express "clear this" with ``None`` alone, because
    ``None`` is also what an absent optional field deserialises to.
    """

    def __repr__(self) -> str:
        return "UNSET"


UNSET = UnsetType()


class ArticleHandlerInterface(ABC):
    """Service layer for Article and Channel write operations.

    All write paths originating in the API layer (article CRUD, publish,
    visibility transitions, channel management) MUST go through this
    interface — route handlers do not touch ORM managers directly.
    """

    # ---- Articles ----

    @abstractmethod
    def create_draft(
        self,
        *,
        author_id: UUID,
        project_id: UUID | None = None,
        channel_id: UUID | None = None,
        title: str = "",
        body: str = "",
    ) -> Article:
        """A new draft: on `project_id` in `channel_id`, or with neither an
        author-owned one. A project without a channel, or a channel without a
        project, is a caller error."""

    @abstractmethod
    def update_article(
        self,
        article_id: UUID,
        *,
        title: str | None = None,
        body: str | None = None,
        summary: str | None = None,
        listing_image_id: UUID | None | UnsetType = UNSET,
        # Same reason as listing_image_id: null clears the framing back to the
        # default 16:9 centred rectangle.
        listing_crop: dict[str, float] | None | UnsetType = UNSET,
        channel_id: UUID | None = None,
        published_at: datetime | None = None,
    ) -> Article: ...

    @abstractmethod
    def publish(
        self,
        article_id: UUID,
        *,
        published_at: datetime | None = None,
    ) -> Article:
        """Draft → published: assign the slug, settle visibility, fan out.

        An author-owned article is attached to its author's personal channel
        here, creating the channel on the author's first publish, so that the
        fan-out reads `article.channel` the same way for both kinds.
        """

    @abstractmethod
    def delete_article(self, article_id: UUID) -> None: ...

    @abstractmethod
    def set_global_visibility(self, article_id: UUID, value: str) -> Article: ...

    # ---- Channels ----

    @abstractmethod
    def add_channel(self, project_id: UUID, name: str) -> Channel: ...

    @abstractmethod
    def rename_channel(self, channel_id: UUID, new_name: str) -> Channel: ...

    @abstractmethod
    def delete_channel(self, channel_id: UUID) -> None: ...

    @abstractmethod
    def bulk_reassign_articles(
        self,
        source_channel_id: UUID,
        target_channel_id: UUID,
    ) -> int: ...
