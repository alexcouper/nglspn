from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from apps.notifications.models import Notification
from services.notifications.query_interface import NotificationQueryInterface

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet


def _unread_qs(user_id: UUID) -> QuerySet[Notification]:
    return Notification.objects.filter(
        recipient_id=user_id, in_app_read_at__isnull=True
    )


class DjangoNotificationQuery(NotificationQueryInterface):
    def list_unread_for_user(self, user_id: UUID) -> QuerySet[Notification]:
        return (
            _unread_qs(user_id)
            .select_related(
                "discussion",
                "discussion__author",
                "discussion__parent",
                "discussion__parent__author",
                "discussion__project",
            )
            .order_by("-discussion__created_at")
        )

    def count_unread_groups_for_user(self, user_id: UUID) -> int:
        # Root id is discussion.parent_id when present, else discussion.id.
        rows = _unread_qs(user_id).values_list("discussion_id", "discussion__parent_id")
        roots: set[UUID] = set()
        for discussion_id, parent_id in rows:
            roots.add(parent_id or discussion_id)
        return len(roots)

    def unread_rows_for_thread(
        self, user_id: UUID, root_discussion_id: UUID
    ) -> QuerySet[Notification]:
        return _unread_qs(user_id).filter(
            Q(discussion_id=root_discussion_id)
            | Q(discussion__parent_id=root_discussion_id)
        )
