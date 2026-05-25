from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.notifications.models import Notification


class NotificationQueryInterface(ABC):
    @abstractmethod
    def list_unread_for_user(self, user_id: UUID) -> QuerySet[Notification]: ...

    @abstractmethod
    def list_unread_articles_for_user(
        self, user_id: UUID
    ) -> QuerySet[Notification]: ...

    @abstractmethod
    def count_unread_groups_for_user(self, user_id: UUID) -> int: ...

    @abstractmethod
    def unread_rows_for_thread(
        self, user_id: UUID, root_discussion_id: UUID
    ) -> QuerySet[Notification]: ...
