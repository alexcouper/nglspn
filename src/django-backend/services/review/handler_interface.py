from abc import ABC, abstractmethod
from uuid import UUID


class ReviewHandlerInterface(ABC):
    @abstractmethod
    def end_review_period(self, competition_id: UUID) -> int:
        """Transition all IN_PROGRESS reviews for the competition to ENDED.

        Returns the number of reviewer rows transitioned.
        """
