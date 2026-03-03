from abc import ABC, abstractmethod
from uuid import UUID


class NotificationHandlerInterface(ABC):
    @abstractmethod
    def create_notifications_for_discussion(self, discussion_id: UUID) -> None: ...

    @abstractmethod
    def send_immediate_notifications(self) -> None: ...

    @abstractmethod
    def send_batch_notifications(self, cadence: str) -> None: ...
