from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from apps.projects.models import Project


@dataclass(frozen=True)
class FollowState:
    is_followed: bool
    created_at: datetime | None = None


@dataclass(frozen=True)
class ChannelFollowState:
    channel_id: UUID
    channel_name: str
    followed: bool


@dataclass(frozen=True)
class FollowWithPreferences:
    project_slug: str
    project_title: str
    project_hero_image_url: str | None
    created_at: datetime
    channels: list[ChannelFollowState] = field(default_factory=list)


class FollowQueryInterface(ABC):
    @abstractmethod
    def is_followed(self, user_id: UUID | None, project: Project) -> bool: ...

    @abstractmethod
    def get_state(self, user_id: UUID | None, project: Project) -> FollowState: ...

    @abstractmethod
    def list_user_follows(self, user_id: UUID) -> list[FollowWithPreferences]: ...

    @abstractmethod
    def get_follow_preferences(
        self, user_id: UUID, project_slug: str
    ) -> FollowWithPreferences | None: ...
