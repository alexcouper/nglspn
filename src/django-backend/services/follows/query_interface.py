from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from apps.projects.models import Project

FollowTarget = Literal["project", "user"]


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
    """One row of the Following page: a followed project or a followed person.

    `target` says which; the other side's fields are None. `channels` is the
    target's channels — a person has at most one, and none until they publish.
    """

    target: FollowTarget
    created_at: datetime
    project_slug: str | None = None
    project_title: str | None = None
    project_hero_image_url: str | None = None
    user_id: UUID | None = None
    user_name: str | None = None
    user_avatar_url: str | None = None
    channels: list[ChannelFollowState] = field(default_factory=list)


class FollowQueryInterface(ABC):
    @abstractmethod
    def is_followed(self, user_id: UUID | None, project: Project) -> bool: ...

    @abstractmethod
    def is_following_user(self, user_id: UUID | None, followed_user_id: UUID) -> bool:
        """Whether `user_id` follows the person `followed_user_id`. Anonymous is
        never following."""

    @abstractmethod
    def get_state(self, user_id: UUID | None, project: Project) -> FollowState: ...

    @abstractmethod
    def list_user_follows(self, user_id: UUID) -> list[FollowWithPreferences]: ...

    @abstractmethod
    def get_follow_preferences(
        self, user_id: UUID, project_slug: str
    ) -> FollowWithPreferences | None: ...
