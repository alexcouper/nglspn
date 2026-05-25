from uuid import UUID

from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.routers._helpers import (
    get_optional_user,
    require_full_edit,
    resolve_visible_project_or_404,
)
from api.schemas.channel import (
    ChannelConflictResponse,
    ChannelCreate,
    ChannelReassign,
    ChannelReassignResponse,
    ChannelRename,
    ChannelResponse,
)
from api.schemas.errors import Error
from apps.follows.models import Channel
from services import HANDLERS, REPO
from services.articles.exceptions import (
    ChannelHasArticlesError,
    ChannelNotFoundError,
    ChannelOnWrongProjectError,
    DuplicateChannelNameError,
    LastChannelError,
)

router = Router()


@router.get(
    "/{slug}/channels",
    response={200: list[ChannelResponse], 404: Error},
    tags=["Channels"],
)
def list_channels(
    request: HttpRequest,
    slug: str,
) -> list[Channel] | tuple[int, dict[str, str]]:
    user = get_optional_user(request)
    project = resolve_visible_project_or_404(slug, user)
    if isinstance(project, tuple):
        return project
    return list(REPO.articles.list_channels_for_project(project.id))


@router.post(
    "/{slug}/channels",
    response={
        201: ChannelResponse,
        401: Error,
        403: Error,
        404: Error,
        409: Error,
    },
    auth=auth,
    tags=["Channels"],
)
def create_channel(
    request: HttpRequest,
    slug: str,
    payload: ChannelCreate,
) -> tuple[int, Channel] | tuple[int, dict[str, str]]:
    project = require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    try:
        channel = HANDLERS.articles.add_channel(project.id, payload.name)
    except DuplicateChannelNameError:
        return 409, {"detail": "A channel with that name already exists"}
    return 201, channel


@router.patch(
    "/{slug}/channels/{channel_id}",
    response={
        200: ChannelResponse,
        401: Error,
        403: Error,
        404: Error,
        409: Error,
    },
    auth=auth,
    tags=["Channels"],
)
def rename_channel(
    request: HttpRequest,
    slug: str,
    channel_id: UUID,
    payload: ChannelRename,
) -> Channel | tuple[int, dict[str, str]]:
    project = require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    if REPO.articles.get_channel_in_project(project.id, channel_id) is None:
        return 404, {"detail": "Channel not found"}
    try:
        return HANDLERS.articles.rename_channel(channel_id, payload.name)
    except ChannelNotFoundError:
        return 404, {"detail": "Channel not found"}
    except DuplicateChannelNameError:
        return 409, {"detail": "A channel with that name already exists"}


@router.delete(
    "/{slug}/channels/{channel_id}",
    response={
        204: None,
        401: Error,
        403: Error,
        404: Error,
        409: ChannelConflictResponse,
    },
    auth=auth,
    tags=["Channels"],
)
def delete_channel(
    request: HttpRequest,
    slug: str,
    channel_id: UUID,
) -> tuple[int, None] | tuple[int, dict[str, object]]:
    project = require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    if REPO.articles.get_channel_in_project(project.id, channel_id) is None:
        return 404, {"detail": "Channel not found"}
    try:
        HANDLERS.articles.delete_channel(channel_id)
    except ChannelNotFoundError:
        return 404, {"detail": "Channel not found"}
    except ChannelHasArticlesError as exc:
        return 409, {
            "detail": "Channel still has articles",
            "article_count": exc.article_count,
        }
    except LastChannelError:
        return 409, {
            "detail": "Cannot delete the last channel on a project",
            "article_count": None,
        }
    return 204, None


@router.post(
    "/{slug}/channels/{channel_id}/reassign",
    response={
        200: ChannelReassignResponse,
        401: Error,
        403: Error,
        404: Error,
        422: Error,
    },
    auth=auth,
    tags=["Channels"],
)
def reassign_channel(
    request: HttpRequest,
    slug: str,
    channel_id: UUID,
    payload: ChannelReassign,
) -> ChannelReassignResponse | tuple[int, dict[str, str]]:
    project = require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    if REPO.articles.get_channel_in_project(project.id, channel_id) is None:
        return 404, {"detail": "Channel not found"}
    if (
        REPO.articles.get_channel_in_project(project.id, payload.target_channel_id)
        is None
    ):
        return 422, {"detail": "Target channel must belong to the same project"}
    try:
        reassigned = HANDLERS.articles.bulk_reassign_articles(
            channel_id, payload.target_channel_id
        )
    except ChannelNotFoundError:
        return 404, {"detail": "Channel not found"}
    except ChannelOnWrongProjectError:
        return 422, {"detail": "Target channel must belong to the same project"}
    return ChannelReassignResponse(reassigned=reassigned)
