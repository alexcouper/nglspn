from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.articles.models import Article
    from apps.projects.models import Project
    from apps.users.models import User, UserAvatar


@dataclass(frozen=True)
class UserProjectItem:
    """A project on a user's public profile, with the user's role on it."""

    project: Project
    role: str
    category_name: str | None
    main_image_thumb_url: str | None


class UserQueryInterface(ABC):
    @abstractmethod
    def get_by_id(self, user_id: UUID) -> User: ...

    @abstractmethod
    def get_active_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    def email_exists(self, email: str) -> bool: ...

    @abstractmethod
    def kennitala_exists(self, kennitala: str) -> bool: ...

    @abstractmethod
    def list_opted_in_for_broadcast_type(self, email_type: str) -> QuerySet: ...

    @abstractmethod
    def get_community_user(self) -> User: ...

    @abstractmethod
    def get_pending_avatar(self, user: User, avatar_id: UUID) -> UserAvatar | None:
        """A reservation the user made that has not been completed, or None.

        Scoped to the user so one account can not complete another's upload.
        """

    @abstractmethod
    def list_public_projects_for(self, user_id: UUID) -> list[UserProjectItem]:
        """Approved projects the user contributes to, owners first, newest first.

        Only `approved` — the same rule as every public project read — and the
        same for the owner looking at their own profile: drafts belong on
        My Projects.
        """

    @abstractmethod
    def list_public_articles_for(self, user_id: UUID) -> QuerySet[Article]:
        """Globally visible articles the user wrote on approved projects, newest
        first. The project check keeps the list free of links that would 404.
        """
