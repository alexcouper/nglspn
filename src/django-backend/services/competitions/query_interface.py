from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from apps.projects.models import Competition
from services.project.query_interface import ProjectListItem


@dataclass(frozen=True)
class CompetitionOverviewItem:
    competition: Competition
    project_count: int
    pending_projects_count: int


@dataclass(frozen=True)
class CompetitionDetailItem:
    competition: Competition
    project_items: list[ProjectListItem] = field(default_factory=list)
    winner_item: ProjectListItem | None = None
    project_count: int = 0
    pending_projects_count: int = 0


@dataclass(frozen=True)
class CompetitionHighlightItem:
    competition: Competition
    project_count: int


class CompetitionQueryInterface(ABC):
    @abstractmethod
    def list_all(self) -> list[CompetitionOverviewItem]: ...

    @abstractmethod
    def list_with_projects(self) -> list[CompetitionDetailItem]: ...

    @abstractmethod
    def get_by_id_or_slug(self, identifier: str) -> CompetitionDetailItem: ...

    @abstractmethod
    def list_highlights(self) -> list[CompetitionHighlightItem]: ...

    @abstractmethod
    def count_pending_projects(self) -> int: ...
