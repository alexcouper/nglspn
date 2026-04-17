from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.text import slugify
from ninja import Query, Router

from api.auth.security import auth
from api.schemas.errors import Error
from api.schemas.tag import (
    TagCategoryResponse,
    TagGroupedResponse,
    TagResponse,
    TagSuggestRequest,
    TagWithCategoryResponse,
)
from apps.tags.models import Tag, TagCategory
from services import HANDLERS, REPO
from services.tags.exceptions import (
    DuplicateTagNameError,
    DuplicateTagSlugError,
    TagAlreadyApprovedError,
    TagAlreadyRejectedError,
    TagCategoryNotFoundError,
    TagNotFoundError,
    TagRejectedError,
)

router = Router()


def _tag_to_response(tag: Any) -> dict[str, Any]:
    return {
        "id": tag.id,
        "name": tag.name,
        "slug": tag.slug,
        "description": tag.description,
        "color": tag.color,
        "category_id": tag.category.id if tag.category else None,
        "category_slug": tag.category.slug if tag.category else None,
        "status": tag.status,
    }


@router.get("", response={200: list[TagResponse]}, tags=["Tags"])
def list_tags(request: HttpRequest) -> QuerySet[Tag]:
    return REPO.tags.list_non_rejected()


@router.get("/categories", response={200: list[TagCategoryResponse]}, tags=["Tags"])
def list_categories(request: HttpRequest) -> QuerySet[TagCategory]:
    return REPO.tags.list_categories()


@router.get("/grouped", response={200: list[TagGroupedResponse]}, tags=["Tags"])
def list_tags_grouped(
    request: HttpRequest,
    with_projects: bool = Query(False),  # noqa: FBT001, FBT003
) -> list[dict[str, Any]]:
    return REPO.tags.list_grouped(with_projects=with_projects)


@router.post(
    "/suggest",
    response={201: TagWithCategoryResponse, 400: Error, 401: Error},
    auth=auth,
    tags=["Tags"],
)
def suggest_tag(
    request: HttpRequest, payload: TagSuggestRequest
) -> tuple[int, dict[str, Any]]:
    slug = slugify(payload.name)

    try:
        tag = HANDLERS.tags.suggest(
            name=payload.name,
            slug=slug,
            description=payload.description,
            color=payload.color,
            category_id=payload.category_id,
            created_by_id=request.auth.id,
        )
    except TagCategoryNotFoundError:
        return 400, {"detail": "Invalid category"}
    except DuplicateTagNameError:
        return 400, {"detail": "A tag with this name already exists"}
    except DuplicateTagSlugError:
        return 400, {"detail": "A tag with this slug already exists"}

    return 201, _tag_to_response(tag)


@router.get(
    "/admin/pending",
    response={200: list[TagWithCategoryResponse], 401: Error, 403: Error},
    auth=auth,
    tags=["Tags Admin"],
)
def list_pending_tags(
    request: HttpRequest,
) -> list[dict[str, Any]] | tuple[int, dict[str, str]]:
    if not request.auth.is_staff:
        return 403, {"detail": "Admin access required"}

    tags = REPO.tags.list_pending()
    return [_tag_to_response(tag) for tag in tags]


@router.put(
    "/admin/{tag_id}/approve",
    response={
        200: TagWithCategoryResponse,
        400: Error,
        401: Error,
        403: Error,
        404: Error,
    },
    auth=auth,
    tags=["Tags Admin"],
)
def approve_tag(
    request: HttpRequest, tag_id: str
) -> dict[str, Any] | tuple[int, dict[str, str]]:
    if not request.auth.is_staff:
        return 403, {"detail": "Admin access required"}

    try:
        tag = HANDLERS.tags.approve(UUID(tag_id), request.auth.id)
    except TagNotFoundError:
        return 404, {"detail": "Tag not found"}
    except TagAlreadyApprovedError:
        return 400, {"detail": "Tag is already approved"}
    except TagRejectedError:
        return 400, {"detail": "Cannot approve a rejected tag"}

    return _tag_to_response(tag)


@router.put(
    "/admin/{tag_id}/reject",
    response={
        200: TagWithCategoryResponse,
        400: Error,
        401: Error,
        403: Error,
        404: Error,
    },
    auth=auth,
    tags=["Tags Admin"],
)
def reject_tag(
    request: HttpRequest, tag_id: str
) -> dict[str, Any] | tuple[int, dict[str, str]]:
    if not request.auth.is_staff:
        return 403, {"detail": "Admin access required"}

    try:
        tag = HANDLERS.tags.reject(UUID(tag_id), request.auth.id)
    except TagNotFoundError:
        return 404, {"detail": "Tag not found"}
    except TagAlreadyRejectedError:
        return 400, {"detail": "Tag is already rejected"}

    return _tag_to_response(tag)
