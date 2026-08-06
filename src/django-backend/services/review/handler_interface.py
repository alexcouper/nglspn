from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID


class ReviewHandlerInterface(ABC):
    @abstractmethod
    def end_review_period(self, competition_id: UUID) -> int:
        """Transition all IN_PROGRESS reviews for the competition to ENDED.

        Returns the number of reviewer rows transitioned.
        """

    @abstractmethod
    def replace_ballot(
        self,
        user_id: UUID,
        competition_id: UUID,
        project_ids: Sequence[UUID],
    ) -> None:
        """Replace a reviewer's ballot with the given projects, in payload order.

        Positions are numbered contiguously from 1; projects left out of the
        payload get no row. An empty payload clears the ballot.

        Raises ReviewerNotAssignedError, ReviewClosedError, DuplicateProjectError
        or ProjectNotInCompetitionError; on any of those nothing is written.
        """
