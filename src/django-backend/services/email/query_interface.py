from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from apps.emails.models import BroadcastEmail


class EmailQueryInterface(ABC):
    @abstractmethod
    def render_broadcast_email(self, broadcast: BroadcastEmail) -> tuple[str, str]: ...

    @abstractmethod
    def resolve_broadcast_recipients(self, broadcast: BroadcastEmail) -> QuerySet: ...
