from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.articles.models import Article
    from apps.follows.models import Channel


class ArticleQueryInterface(ABC):
    @abstractmethod
    def get_by_id(self, article_id: UUID) -> Article | None: ...

    @abstractmethod
    def get_by_project_and_slug(
        self,
        project_slug: str,
        article_slug: str,
    ) -> Article | None: ...

    @abstractmethod
    def for_project(
        self,
        project_id: UUID,
        *,
        include_drafts: bool = False,
    ) -> QuerySet[Article]: ...

    @abstractmethod
    def list_channels_for_project(self, project_id: UUID) -> QuerySet[Channel]: ...

    @abstractmethod
    def get_channel_in_project(
        self, project_id: UUID, channel_id: UUID
    ) -> Channel | None: ...
