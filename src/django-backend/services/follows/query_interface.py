from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.projects.models import Project


@dataclass(frozen=True)
class FollowState:
    is_followed: bool
    created_at: datetime | None = None


class FollowQueryInterface(ABC):
    @abstractmethod
    def is_followed(self, user_id: UUID | None, project: Project) -> bool: ...

    @abstractmethod
    def get_state(self, user_id: UUID | None, project: Project) -> FollowState: ...
