from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from apps.projects.models import Project, ProjectContributor


@dataclass(frozen=True)
class ProjectListItem:
    project: Project
    main_image_url: str | None = None
    main_image_thumb_url: str | None = None
    main_image_variants: list = field(default_factory=list)
    tags: list = field(default_factory=list)


@dataclass(frozen=True)
class DiscoverProjectItem:
    project: Project
    icon_url: str | None = None
    hero_banner_url: str | None = None
    in_use_image_url: str | None = None
    category_name: str | None = None
    category_slug: str | None = None
    discussion_count: int = 0


@dataclass(frozen=True)
class WinnerItem:
    project: Project
    icon_url: str | None = None
    hero_banner_url: str | None = None
    in_use_image_url: str | None = None
    competition_name: str = ""
    competition_slug: str = ""
    competition_submission_deadline: date | None = None


@dataclass(frozen=True)
class CategoryItem:
    id: UUID
    name: str
    slug: str
    project_count: int


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
    def get_by_identifier(self, identifier: str) -> Project: ...

    @abstractmethod
    def get_for_owner(self, project_id: UUID, owner_id: UUID) -> Project: ...

    @abstractmethod
    def user_can_edit(self, project_id: UUID | None, user_id: UUID | None) -> bool: ...

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
    def list_suggestions_for(self, user_id: UUID) -> QuerySet[Project]: ...

    @abstractmethod
    def list_notifiable_contributors(
        self, project_id: UUID
    ) -> QuerySet[ProjectContributor]: ...

    @abstractmethod
    def count_pending(self) -> int: ...

    @abstractmethod
    def get_project_with_owner(self, project_id: UUID) -> dict[str, Any]: ...

    @abstractmethod
    def list_featured(self) -> list[DiscoverProjectItem]: ...

    @abstractmethod
    def list_new_arrivals(
        self, *, min_count: int = 5, days: int = 30
    ) -> list[DiscoverProjectItem]: ...

    @abstractmethod
    def list_winners(self) -> list[WinnerItem]: ...

    @abstractmethod
    def list_most_discussed(self) -> list[DiscoverProjectItem]: ...

    @abstractmethod
    def list_by_category(
        self, slug: str, sort: str = "newest"
    ) -> list[DiscoverProjectItem]: ...

    @abstractmethod
    def list_categories(self) -> list[CategoryItem]: ...
