from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.schemas.notification import (
    MarkAllReadResponse,
    MarkThreadReadRequest,
    MarkThreadReadResponse,
    NotificationGroupResponse,
    NotificationSummaryResponse,
)
from services import HANDLERS

router = Router()

_DEFAULT_GROUP_LIMIT = 50


@router.get(
    "/summary",
    response={200: NotificationSummaryResponse},
    auth=auth,
    tags=["Notifications"],
)
def get_summary(request: HttpRequest) -> NotificationSummaryResponse:
    summary = HANDLERS.notifications.get_unread_summary_for_user(request.auth.id)
    return NotificationSummaryResponse.from_dataclass(summary)


@router.get(
    "/groups",
    response={200: list[NotificationGroupResponse]},
    auth=auth,
    tags=["Notifications"],
)
def list_groups(
    request: HttpRequest,
    limit: int = _DEFAULT_GROUP_LIMIT,
) -> list[NotificationGroupResponse]:
    groups = HANDLERS.notifications.list_unread_groups_for_user(
        request.auth.id, limit=limit
    )
    return [NotificationGroupResponse.from_dataclass(g) for g in groups]


@router.post(
    "/mark-thread-read",
    response={200: MarkThreadReadResponse},
    auth=auth,
    tags=["Notifications"],
)
def mark_thread_read(
    request: HttpRequest,
    payload: MarkThreadReadRequest,
) -> MarkThreadReadResponse:
    marked = HANDLERS.notifications.mark_thread_read_for_user(
        request.auth.id, payload.root_discussion_id
    )
    return MarkThreadReadResponse(marked=marked)


@router.post(
    "/mark-all-read",
    response={200: MarkAllReadResponse},
    auth=auth,
    tags=["Notifications"],
)
def mark_all_read(request: HttpRequest) -> MarkAllReadResponse:
    marked = HANDLERS.notifications.mark_all_read_for_user(request.auth.id)
    return MarkAllReadResponse(marked=marked)
