from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import QuerySet

from apps.discussions.models import Discussion
from services.discussions.exceptions import DiscussionNotFoundError
from services.discussions.query_interface import DiscussionQueryInterface

if TYPE_CHECKING:
    from uuid import UUID


def _base_queryset() -> QuerySet[Discussion]:
    return Discussion.objects.select_related("author")


class DjangoDiscussionQuery(DiscussionQueryInterface):
    def list_for_project(self, project_id: UUID) -> QuerySet[Discussion]:
        return (
            _base_queryset()
            .filter(project_id=project_id, parent__isnull=True)
            .prefetch_related("replies", "replies__author")
            .order_by("-created_at")
        )

    def get_by_id(self, discussion_id: UUID) -> Discussion:
        try:
            return (
                _base_queryset()
                .prefetch_related("replies", "replies__author")
                .get(id=discussion_id)
            )
        except Discussion.DoesNotExist:
            raise DiscussionNotFoundError from None
