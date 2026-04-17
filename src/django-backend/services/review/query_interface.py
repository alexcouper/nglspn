from abc import ABC, abstractmethod
from uuid import UUID

from apps.projects.models import Competition, CompetitionReviewer, Project


class ReviewQueryInterface(ABC):
    @abstractmethod
    def list_reviewer_assignments(self, user_id: UUID) -> list[CompetitionReviewer]: ...

    @abstractmethod
    def get_reviewer_assignment(
        self, user_id: UUID, competition_id: UUID
    ) -> CompetitionReviewer | None: ...

    @abstractmethod
    def get_competition_with_projects(self, competition_id: UUID) -> Competition: ...

    @abstractmethod
    def get_reviewer_rankings(
        self, user_id: UUID, competition_id: UUID
    ) -> dict[UUID, int]: ...

    @abstractmethod
    def get_competition_project_ids(
        self, competition_id: UUID, excluded_statuses: list[str]
    ) -> set[UUID]: ...

    @abstractmethod
    def get_review_project(self, user_id: UUID, project_id: UUID) -> Project: ...
