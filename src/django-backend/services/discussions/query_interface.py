from abc import ABC, abstractmethod
from uuid import UUID

from django.db.models import QuerySet

from apps.discussions.models import Discussion


class DiscussionQueryInterface(ABC):
    @abstractmethod
    def list_for_project(self, project_id: UUID) -> QuerySet[Discussion]: ...

    @abstractmethod
    def get_by_id(self, discussion_id: UUID) -> Discussion: ...
