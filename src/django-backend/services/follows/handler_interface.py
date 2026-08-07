from abc import ABC, abstractmethod
from uuid import UUID

from apps.projects.models import Project
from services.follows.query_interface import ChannelFollowState, FollowState


class FollowHandlerInterface(ABC):
    @abstractmethod
    def follow(self, user_id: UUID, project: Project) -> FollowState:
        """Create a Follow (idempotent). Returns the current state.

        On first follow, also creates a FollowedChannel row for every channel
        currently on the project. Re-following an already-followed project is
        a no-op: existing FollowedChannel rows are left alone, and no rows
        are added for channels that were created after the original follow.

        That includes a Follow whose channels have all gone (see
        ``unfollow_channel``): re-following writes nothing, so the user stays
        followed-with-nothing-ticked until they tick a channel themselves.
        Accepted; see design decision 6 in
        openspec/changes/archive/2026-08-07-simplify-follow-and-cadence/design.md.
        """

    @abstractmethod
    def unfollow(self, user_id: UUID, project: Project) -> None:
        """Hard-delete the Follow (idempotent — no-op when absent)."""

    @abstractmethod
    def follow_channel(
        self, user_id: UUID, project_slug: str, channel_id: UUID
    ) -> ChannelFollowState:
        """Follow a single channel under an existing project Follow.

        Raises ``NotFollowingError`` / ``ChannelNotOnProjectError`` /
        ``services.project.exceptions.ProjectNotFoundError`` as appropriate.
        Idempotent — a second invocation returns the existing state.
        """

    @abstractmethod
    def unfollow_channel(
        self, user_id: UUID, project_slug: str, channel_id: UUID
    ) -> FollowState:
        """Hard-delete a FollowedChannel row, returning the project's state.

        When no followed channels remain the project Follow is deleted too —
        this is the one path where the user has just asked to stop — and the
        returned state has ``is_followed=False``. Idempotent while other
        channels remain; once the Follow is gone a repeat raises
        ``NotFollowingError``.

        That is a rule about this method, not an invariant on the table.
        Deleting a Channel cascades FollowedChannel rows away, two concurrent
        calls here can each miss the other's delete, and follows/0004 left
        emptied rows behind on purpose. A Follow with no channels is tolerated:
        it notifies about nothing (every actor selects FollowedChannel), but
        the reads still report it as followed. See design decision 6 in
        openspec/changes/archive/2026-08-07-simplify-follow-and-cadence/design.md.
        """
