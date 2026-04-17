from abc import ABC, abstractmethod
from uuid import UUID


class ReviewHandlerInterface(ABC):
    @abstractmethod
    def update_rankings(
        self,
        *,
        user_id: UUID,
        competition_id: UUID,
        project_ids: list[UUID],
    ) -> None: ...

    @abstractmethod
    def update_review_status(
        self,
        *,
        user_id: UUID,
        competition_id: UUID,
        status: str,
    ) -> None: ...
