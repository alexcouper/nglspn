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
        project_id: UUID,
        channel_id: UUID,
        author_id: UUID,
        title: str = "",
        body: str = "",
        hero_image_id: UUID | None = None,
        hero_crop: dict[str, float] | None = None,
    ) -> Article: ...

    @abstractmethod
    def update_article(
        self,
        article_id: UUID,
        *,
        title: str | None = None,
        body: str | None = None,
        summary: str | None = None,
        hero_image_id: UUID | None | UnsetType = UNSET,
        # Same reason as hero_image_id: null clears the hero framing, or drops a
        # card override back to the value derived from the hero.
        hero_crop: dict[str, float] | None | UnsetType = UNSET,
        card_crop: dict[str, float] | None | UnsetType = UNSET,
        channel_id: UUID | None = None,
        published_at: datetime | None = None,
    ) -> Article: ...

    @abstractmethod
    def publish(
        self,
        article_id: UUID,
        *,
        published_at: datetime | None = None,
    ) -> Article: ...

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
