from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from apps.projects.models import Project


class ProjectQueryInterface(ABC):
    @abstractmethod
    def get_by_id(self, project_id: UUID) -> Project: ...

    @abstractmethod
    def get_for_owner(self, project_id: UUID, owner_id: UUID) -> Project: ...

    @abstractmethod
    def list_approved(
        self,
        *,
        tags: list[str] | None = None,
        tech_stack: list[str] | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]: ...

    @abstractmethod
    def list_for_owner(self, owner_id: UUID) -> QuerySet[Project]: ...

    @abstractmethod
    def list_featured(self, limit: int = 10) -> QuerySet[Project]: ...

    @abstractmethod
    def list_trending(self, limit: int = 10) -> QuerySet[Project]: ...

    @abstractmethod
    def count_pending(self) -> int: ...

    @abstractmethod
    def get_project_with_owner(self, project_id: UUID) -> dict[str, Any]: ...
