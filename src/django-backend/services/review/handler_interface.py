from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from apps.projects.models import ReviewStatus


class ReviewHandlerInterface(ABC):
    @abstractmethod
    def replace_ballot(
        self,
        user_id: UUID,
        competition_id: UUID,
        project_ids: Sequence[UUID],
    ) -> None:
        """Replace a reviewer's ballot with the given projects, in payload order.

        Positions are numbered contiguously from 1; projects left out of the
        payload get no row. An empty payload clears the ballot. The first save
        creates the user's review.

        Raises ReviewerNotAssignedError, ReviewClosedError, DuplicateProjectError
        or ProjectNotInCompetitionError; on any of those nothing is written.
        """

    @abstractmethod
    def set_review_status(
        self,
        user_id: UUID,
        competition_id: UUID,
        status: ReviewStatus,
    ) -> None:
        """Set the user's review status, creating the review if needed.

        Completing without ranking anything is an abstention and is counted.
        Raises ReviewerNotAssignedError or ReviewClosedError.
        """
