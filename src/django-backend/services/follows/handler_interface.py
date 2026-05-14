from abc import ABC, abstractmethod
from uuid import UUID

from apps.projects.models import Project
from services.follows.query_interface import FollowState


class FollowHandlerInterface(ABC):
    @abstractmethod
    def follow(self, user_id: UUID, project: Project) -> FollowState:
        """Create a Follow (idempotent). Returns the current state."""

    @abstractmethod
    def unfollow(self, user_id: UUID, project: Project) -> None:
        """Hard-delete the Follow (idempotent — no-op when absent)."""
