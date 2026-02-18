from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.users.models import User


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
