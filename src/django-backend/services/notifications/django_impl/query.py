from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import F, Q
from django.db.models.functions import Coalesce

from apps.notifications.models import Notification
from services.notifications.query_interface import NotificationQueryInterface

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet


def _unread_qs(user_id: UUID) -> QuerySet[Notification]:
    return Notification.objects.filter(
        recipient_id=user_id, in_app_read_at__isnull=True
    )


def _unread_discussion_qs(user_id: UUID) -> QuerySet[Notification]:
    """Discussion-only slice — the in-app surfaces that branch on `kind`
    will be extended in a later chunk; for now article rows are excluded
    here so the existing groups/summary path keeps working unchanged."""
    return _unread_qs(user_id).filter(discussion__isnull=False)


class DjangoNotificationQuery(NotificationQueryInterface):
    def list_unread_for_user(self, user_id: UUID) -> QuerySet[Notification]:
        return (
            _unread_discussion_qs(user_id)
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
        return (
            _unread_discussion_qs(user_id)
            .annotate(root=Coalesce(F("discussion__parent_id"), F("discussion_id")))
            .values("root")
            .distinct()
            .count()
        )

    def unread_rows_for_thread(
        self, user_id: UUID, root_discussion_id: UUID
    ) -> QuerySet[Notification]:
        return _unread_discussion_qs(user_id).filter(
            Q(discussion_id=root_discussion_id)
            | Q(discussion__parent_id=root_discussion_id)
        )
