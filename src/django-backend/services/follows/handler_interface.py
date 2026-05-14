from abc import ABC, abstractmethod
from uuid import UUID

from apps.projects.models import Project
from services.follows.query_interface import ChannelPreferenceState, FollowState


class FollowHandlerInterface(ABC):
    @abstractmethod
    def follow(self, user_id: UUID, project: Project) -> FollowState:
        """Create a Follow (idempotent). Returns the current state."""

    @abstractmethod
    def unfollow(self, user_id: UUID, project: Project) -> None:
        """Hard-delete the Follow (idempotent — no-op when absent).

        When the targeted project is the house project, this SHALL also
        clear the legacy ``email_opt_in_*`` flags on the user.
        """

    @abstractmethod
    def set_channel_preference(
        self,
        user_id: UUID,
        project_slug: str,
        channel_id: UUID,
        *,
        email_enabled: bool | None = None,
        in_app_enabled: bool | None = None,
    ) -> ChannelPreferenceState:
        """Patch a single FollowChannelPreference row.

        Raises ``EmptyPatchError`` when both fields are None.
        Raises ``NotFollowingError`` / ``ChannelNotOnProjectError`` /
        ``services.project.exceptions.ProjectNotFoundError`` as appropriate.
        """
