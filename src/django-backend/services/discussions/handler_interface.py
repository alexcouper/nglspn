from abc import ABC, abstractmethod
from uuid import UUID

from apps.discussions.models import Discussion


class DiscussionHandlerInterface(ABC):
    @abstractmethod
    def create_discussion(
        self,
        project_id: UUID,
        author_id: UUID,
        body: str,
        parent_id: UUID | None = None,
    ) -> Discussion: ...

    @abstractmethod
    def delete_discussion(
        self, discussion_id: UUID, requesting_user_id: UUID
    ) -> None: ...
