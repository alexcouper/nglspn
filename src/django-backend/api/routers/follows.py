from uuid import UUID

from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.schemas.errors import Error
from api.schemas.follow import (
    FollowChannelPreferencePatch,
    FollowChannelPreferenceResponse,
    FollowResponse,
    FollowStateResponse,
)
from services import HANDLERS, REPO
from services.follows.exceptions import (
    ChannelNotOnProjectError,
    EmptyPatchError,
    NotFollowingError,
)
from services.follows.query_interface import FollowWithPreferences
from services.project.exceptions import ProjectNotFoundError

# Mounted at /api/projects (in api/main.py): handles per-project follow URLs.
router = Router()

# Mounted at /api/follows: handles the user-scoped collection.
collection_router = Router()


def _to_follow_response(item: FollowWithPreferences) -> FollowResponse:
    return FollowResponse(
        project_slug=item.project_slug,
        project_title=item.project_title,
        project_hero_image_url=item.project_hero_image_url,
        created_at=item.created_at,
        channels=[
            FollowChannelPreferenceResponse(
                channel_id=c.channel_id,
                channel_name=c.channel_name,
                email_enabled=c.email_enabled,
                in_app_enabled=c.in_app_enabled,
            )
            for c in item.channels
        ],
    )


@collection_router.get(
    "",
    response={200: list[FollowResponse]},
    auth=auth,
    tags=["Follows"],
)
def list_follows(request: HttpRequest) -> list[FollowResponse]:
    items = REPO.follows.list_user_follows(request.auth.id)
    return [_to_follow_response(item) for item in items]


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


@router.get(
    "/{slug}/follow/preferences",
    response={200: FollowResponse, 404: Error},
    auth=auth,
    tags=["Follows"],
)
def get_follow_preferences(
    request: HttpRequest, slug: str
) -> FollowResponse | tuple[int, dict[str, str]]:
    item = REPO.follows.get_follow_preferences(request.auth.id, slug)
    if item is None:
        return 404, {"detail": "Not following"}
    return _to_follow_response(item)


@router.patch(
    "/{slug}/follow/channels/{channel_id}",
    response={
        200: FollowChannelPreferenceResponse,
        400: Error,
        404: Error,
    },
    auth=auth,
    tags=["Follows"],
)
def patch_follow_channel(
    request: HttpRequest,
    slug: str,
    channel_id: UUID,
    payload: FollowChannelPreferencePatch,
) -> FollowChannelPreferenceResponse | tuple[int, dict[str, str]]:
    try:
        state = HANDLERS.follows.set_channel_preference(
            request.auth.id,
            slug,
            channel_id,
            email_enabled=payload.email_enabled,
            in_app_enabled=payload.in_app_enabled,
        )
    except EmptyPatchError:
        return 400, {"detail": "Provide email_enabled and/or in_app_enabled"}
    except (
        ProjectNotFoundError,
        ChannelNotOnProjectError,
        NotFollowingError,
    ):
        return 404, {"detail": "Not found"}

    return FollowChannelPreferenceResponse(
        channel_id=state.channel_id,
        channel_name=state.channel_name,
        email_enabled=state.email_enabled,
        in_app_enabled=state.in_app_enabled,
    )
