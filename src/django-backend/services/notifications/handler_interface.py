from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from services.notifications import NotificationGroup, NotificationSummary


class NotificationHandlerInterface(ABC):
    @abstractmethod
    def create_notifications_for_discussion(self, discussion_id: UUID) -> None: ...

    @abstractmethod
    def send_batch_notifications(self, cadence: str) -> None: ...

    @abstractmethod
    def list_unread_groups_for_user(
        self, user_id: UUID, limit: int = 50
    ) -> list[NotificationGroup]: ...

    @abstractmethod
    def get_unread_summary_for_user(self, user_id: UUID) -> NotificationSummary: ...

    @abstractmethod
    def mark_thread_read_for_user(
        self, user_id: UUID, root_discussion_id: UUID
    ) -> int: ...

    @abstractmethod
    def mark_all_read_for_user(self, user_id: UUID) -> int: ...

    @abstractmethod
    def delete_old_read_notifications(self) -> int: ...
