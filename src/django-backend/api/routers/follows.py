from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.schemas.errors import Error
from api.schemas.follow import FollowStateResponse
from services import HANDLERS, REPO
from services.project.exceptions import ProjectNotFoundError

router = Router()


@router.post(
    "/{slug}/follow",
    response={200: FollowStateResponse, 404: Error},
    auth=auth,
    tags=["Follows"],
)
def follow_project(
    request: HttpRequest, slug: str
) -> FollowStateResponse | tuple[int, dict[str, str]]:
    try:
        project = REPO.project.get_by_identifier(slug)
    except ProjectNotFoundError:
        return 404, {"detail": "Project not found"}

    state = HANDLERS.follows.follow(request.auth.id, project)
    return FollowStateResponse(
        is_followed=state.is_followed, created_at=state.created_at
    )


@router.delete(
    "/{slug}/follow",
    response={204: None, 404: Error},
    auth=auth,
    tags=["Follows"],
)
def unfollow_project(
    request: HttpRequest, slug: str
) -> tuple[int, None] | tuple[int, dict[str, str]]:
    try:
        project = REPO.project.get_by_identifier(slug)
    except ProjectNotFoundError:
        return 404, {"detail": "Project not found"}

    HANDLERS.follows.unfollow(request.auth.id, project)
    return 204, None
