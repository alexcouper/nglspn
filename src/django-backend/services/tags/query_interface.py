from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.tags.models import Tag, TagCategory


@dataclass(frozen=True)
class CategoryTags:
    category: TagCategory
    tags: list[Tag]


class TagQueryInterface(ABC):
    @abstractmethod
    def list_non_rejected(self) -> QuerySet[Tag]: ...

    @abstractmethod
    def list_categories(self) -> QuerySet[TagCategory]: ...

    @abstractmethod
    def list_grouped(self, *, with_projects: bool = False) -> list[CategoryTags]: ...

    @abstractmethod
    def list_pending(self) -> QuerySet[Tag]: ...

    @abstractmethod
    def get_by_id(self, tag_id: UUID) -> Tag: ...
