from __future__ import annotations

from typing import TYPE_CHECKING

from apps.discussions.models import Discussion
from services.discussions.exceptions import (
    DiscussionNotFoundError,
    NotDiscussionAuthorError,
)
from services.discussions.handler_interface import DiscussionHandlerInterface

if TYPE_CHECKING:
    from uuid import UUID


class DjangoDiscussionHandler(DiscussionHandlerInterface):
    def create_discussion(
        self,
        project_id: UUID,
        author_id: UUID,
        body: str,
        parent_id: UUID | None = None,
    ) -> Discussion:
        if parent_id is not None:
            try:
                parent = Discussion.objects.select_related("project").get(id=parent_id)
            except Discussion.DoesNotExist:
                raise DiscussionNotFoundError from None
            project_id = parent.project_id

        discussion = Discussion.objects.create(
            project_id=project_id,
            author_id=author_id,
            parent_id=parent_id,
            body=body,
        )

        from api.tasks.notifications import (  # noqa: PLC0415
            create_discussion_notifications,
        )

        create_discussion_notifications.enqueue(str(discussion.id))

        return discussion

    def delete_discussion(self, discussion_id: UUID, requesting_user_id: UUID) -> None:
        try:
            discussion = Discussion.objects.get(id=discussion_id)
        except Discussion.DoesNotExist:
            raise DiscussionNotFoundError from None

        if discussion.author_id != requesting_user_id:
            raise NotDiscussionAuthorError

        discussion.delete()
