from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from apps.projects.models import Competition


@dataclass(frozen=True)
class CompetitionHighlight:
    competition: Competition
    project_count: int


class CompetitionQueryInterface(ABC):
    @abstractmethod
    def list_all(self) -> QuerySet[Competition]: ...

    @abstractmethod
    def list_with_projects(self) -> QuerySet[Competition]: ...

    @abstractmethod
    def get_by_id_or_slug(self, identifier: str) -> Competition: ...

    @abstractmethod
    def list_highlights(self) -> list[CompetitionHighlight]: ...

    @abstractmethod
    def count_pending_projects(self) -> int: ...
