from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from apps.tags.models import Tag
    from apps.users.models import User


class TagHandlerInterface(ABC):
    @abstractmethod
    def suggest(
        self,
        *,
        name: str,
        description: str | None,
        color: str | None,
        category_id: UUID,
        created_by: User,
    ) -> Tag: ...

    @abstractmethod
    def approve(self, tag_id: UUID, reviewed_by: User) -> Tag: ...

    @abstractmethod
    def reject(self, tag_id: UUID, reviewed_by: User) -> Tag: ...
