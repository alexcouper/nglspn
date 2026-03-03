from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from apps.discussions.models import Discussion
    from apps.emails.models import BroadcastEmail
    from apps.notifications.models import Notification
    from apps.projects.models import Project
    from apps.users.models import User


class EmailHandlerInterface(ABC):
    @abstractmethod
    def send_verification_email(
        self, user: User, code: str, expires_minutes: int
    ) -> None: ...

    @abstractmethod
    def send_project_approved_email(self, project: Project) -> None: ...

    @abstractmethod
    def send_password_reset_email(
        self, user: User, code: str, expires_minutes: int
    ) -> None: ...

    @abstractmethod
    def send_broadcast(
        self, broadcast: BroadcastEmail, sent_by_user: User
    ) -> tuple[int, int]: ...

    @abstractmethod
    def send_discussion_notification_email(
        self, notification: Notification, discussion: Discussion
    ) -> None: ...

    @abstractmethod
    def send_discussion_digest_email(
        self, notifications: Sequence[Notification]
    ) -> None: ...
