from abc import ABC, abstractmethod
from uuid import UUID

from apps.tags.models import Tag


class TagHandlerInterface(ABC):
    @abstractmethod
    def suggest(
        self,
        *,
        name: str,
        slug: str,
        description: str | None,
        color: str | None,
        category_id: UUID,
        created_by_id: UUID,
    ) -> Tag: ...

    @abstractmethod
    def approve(self, tag_id: UUID, reviewed_by_id: UUID) -> Tag: ...

    @abstractmethod
    def reject(self, tag_id: UUID, reviewed_by_id: UUID) -> Tag: ...
