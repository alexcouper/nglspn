from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from apps.projects.models import Project


@dataclass(frozen=True)
class ProjectListItem:
    project: Project
    main_image_url: str | None = None
    main_image_thumb_url: str | None = None
    tags: list = field(default_factory=list)


@dataclass(frozen=True)
class PaginatedProjects:
    projects: list[ProjectListItem]
    total: int
    page: int
    per_page: int
    pages: int


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
    ) -> PaginatedProjects: ...

    @abstractmethod
    def list_for_owner(self, owner_id: UUID) -> QuerySet[Project]: ...

    @abstractmethod
    def count_pending(self) -> int: ...

    @abstractmethod
    def get_project_with_owner(self, project_id: UUID) -> dict[str, Any]: ...
