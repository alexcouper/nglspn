from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.schemas.discussion import DiscussionCreate, DiscussionResponse, ReplyResponse
from api.schemas.errors import Error
from apps.discussions.models import Discussion
from services import HANDLERS, REPO
from services.discussions.exceptions import (
    DiscussionNotFoundError,
    NotDiscussionAuthorError,
)

router = Router()


@router.get(
    "/{project_id}/discussions",
    response={200: list[DiscussionResponse]},
    auth=auth,
    tags=["Discussions"],
)
def list_discussions(
    request: HttpRequest,
    project_id: str,
) -> QuerySet[Discussion]:
    return REPO.discussions.list_for_project(project_id)


@router.post(
    "/{project_id}/discussions",
    response={201: DiscussionResponse, 401: Error},
    auth=auth,
    tags=["Discussions"],
)
def create_discussion(
    request: HttpRequest,
    project_id: str,
    payload: DiscussionCreate,
) -> tuple[int, Discussion]:
    discussion = HANDLERS.discussions.create_discussion(
        project_id=project_id,
        author_id=request.auth.id,
        body=payload.body,
    )
    return 201, discussion


@router.post(
    "/{project_id}/discussions/{discussion_id}/replies",
    response={201: ReplyResponse, 401: Error, 404: Error},
    auth=auth,
    tags=["Discussions"],
)
def reply_to_discussion(
    request: HttpRequest,
    project_id: str,
    discussion_id: str,
    payload: DiscussionCreate,
) -> tuple[int, Discussion] | tuple[int, dict[str, str]]:
    try:
        reply = HANDLERS.discussions.create_discussion(
            project_id=project_id,
            author_id=request.auth.id,
            body=payload.body,
            parent_id=discussion_id,
        )
    except DiscussionNotFoundError:
        return 404, {"detail": "Discussion not found"}
    return 201, reply


@router.delete(
    "/{project_id}/discussions/{discussion_id}",
    response={204: None, 401: Error, 403: Error, 404: Error},
    auth=auth,
    tags=["Discussions"],
)
def delete_discussion(
    request: HttpRequest,
    project_id: str,
    discussion_id: str,
) -> tuple[int, None] | tuple[int, dict[str, str]]:
    try:
        HANDLERS.discussions.delete_discussion(
            discussion_id=discussion_id,
            requesting_user_id=request.auth.id,
        )
    except DiscussionNotFoundError:
        return 404, {"detail": "Discussion not found"}
    except NotDiscussionAuthorError:
        return 403, {"detail": "You can only delete your own discussions"}
    return 204, None
