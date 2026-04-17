from typing import Any

from django.db.models import QuerySet
from django.http import HttpRequest
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


def _tag_with_category(tag: Any) -> dict[str, Any]:
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
def list_tags(request: HttpRequest) -> QuerySet:
    """List all approved and pending tags (excludes rejected)."""
    return REPO.tags.list_non_rejected()


@router.get("/categories", response={200: list[TagCategoryResponse]}, tags=["Tags"])
def list_categories(request: HttpRequest) -> QuerySet:
    """List all active tag categories."""
    return REPO.tags.list_categories()


@router.get("/grouped", response={200: list[TagGroupedResponse]}, tags=["Tags"])
def list_tags_grouped(
    request: HttpRequest,
    with_projects: bool = Query(False),  # noqa: FBT001, FBT003
) -> list[dict[str, Any]]:
    """List tags grouped by category (excludes rejected tags).

    If with_projects=true, only returns tags with at least one approved project.
    """
    grouped = REPO.tags.list_grouped(with_projects=with_projects)

    result = []
    for group in grouped:
        category = group.category
        tags = [
            {
                "id": tag.id,
                "name": tag.name,
                "slug": tag.slug,
                "description": tag.description,
                "color": tag.color,
                "category_id": category.id,
                "category_slug": category.slug,
                "status": tag.status,
            }
            for tag in group.tags
        ]

        # Skip empty categories
        if not tags:
            continue

        result.append(
            {
                "category": {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                    "description": category.description,
                    "display_order": category.display_order,
                },
                "tags": tags,
            }
        )

    return result


@router.post(
    "/suggest",
    response={201: TagWithCategoryResponse, 400: Error, 401: Error, 404: Error},
    auth=auth,
    tags=["Tags"],
)
def suggest_tag(
    request: HttpRequest, payload: TagSuggestRequest
) -> tuple[int, dict[str, Any]]:
    """Suggest a new tag (creates with status=pending, immediately usable)."""
    try:
        tag = HANDLERS.tags.suggest(
            name=payload.name,
            description=payload.description,
            color=payload.color,
            category_id=payload.category_id,
            created_by=request.auth,
        )
    except TagCategoryNotFoundError:
        return 404, {"detail": "Not Found"}
    except DuplicateTagNameError:
        return 400, {"detail": "A tag with this name already exists"}
    except DuplicateTagSlugError:
        return 400, {"detail": "A tag with this slug already exists"}

    return 201, _tag_with_category(tag)


# Admin endpoints for tag approval workflow


@router.get(
    "/admin/pending",
    response={200: list[TagWithCategoryResponse], 401: Error, 403: Error},
    auth=auth,
    tags=["Tags Admin"],
)
def list_pending_tags(
    request: HttpRequest,
) -> list[dict[str, Any]] | tuple[int, dict[str, str]]:
    """List pending tags for review (admin only)."""
    if not request.auth.is_staff:
        return 403, {"detail": "Admin access required"}

    return [_tag_with_category(tag) for tag in REPO.tags.list_pending()]


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
    """Approve a pending tag (admin only)."""
    if not request.auth.is_staff:
        return 403, {"detail": "Admin access required"}

    try:
        tag = HANDLERS.tags.approve(tag_id, request.auth)
    except TagNotFoundError:
        return 404, {"detail": "Not Found"}
    except TagAlreadyApprovedError:
        return 400, {"detail": "Tag is already approved"}
    except TagRejectedError:
        return 400, {"detail": "Cannot approve a rejected tag"}

    return _tag_with_category(tag)


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
    """Reject a tag (admin only). Removes tag from all projects."""
    if not request.auth.is_staff:
        return 403, {"detail": "Admin access required"}

    try:
        tag = HANDLERS.tags.reject(tag_id, request.auth)
    except TagNotFoundError:
        return 404, {"detail": "Not Found"}
    except TagAlreadyRejectedError:
        return 400, {"detail": "Tag is already rejected"}

    return _tag_with_category(tag)
