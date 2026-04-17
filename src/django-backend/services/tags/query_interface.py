from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from apps.tags.models import Tag, TagCategory


class TagQueryInterface(ABC):
    @abstractmethod
    def list_non_rejected(self) -> QuerySet[Tag]: ...

    @abstractmethod
    def list_categories(self) -> QuerySet[TagCategory]: ...

    @abstractmethod
    def list_grouped(self, *, with_projects: bool = False) -> list[dict[str, Any]]: ...

    @abstractmethod
    def list_pending(self) -> QuerySet[Tag]: ...

    @abstractmethod
    def get_by_id(self, tag_id: UUID) -> Tag: ...
