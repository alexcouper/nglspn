from typing import Any

from django.db.models import Prefetch, QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
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
from apps.projects.models import ProjectStatus
from apps.tags.models import Tag, TagCategory, TagStatus

router = Router()


@router.get("", response={200: list[TagResponse]}, tags=["Tags"])
def list_tags(request: HttpRequest) -> QuerySet[Tag]:
    """List all approved and pending tags (excludes rejected)."""
    return Tag.objects.exclude(status=TagStatus.REJECTED)


@router.get("/categories", response={200: list[TagCategoryResponse]}, tags=["Tags"])
def list_categories(request: HttpRequest) -> QuerySet[TagCategory]:
    """List all active tag categories."""
    return TagCategory.objects.filter(is_active=True)


@router.get("/grouped", response={200: list[TagGroupedResponse]}, tags=["Tags"])
def list_tags_grouped(
    request: HttpRequest,
    with_projects: bool = Query(False),  # noqa: FBT001, FBT003
) -> list[dict[str, Any]]:
    """List tags grouped by category (excludes rejected tags).

    If with_projects=true, only returns tags with at least one approved project.
    """
    # Build tag queryset with filters applied at database level
    tag_queryset = Tag.objects.exclude(status=TagStatus.REJECTED)
    if with_projects:
        tag_queryset = tag_queryset.filter(projects__status=ProjectStatus.APPROVED)
    tag_queryset = tag_queryset.distinct()

    categories = TagCategory.objects.filter(is_active=True).prefetch_related(
        Prefetch("tags", queryset=tag_queryset)
    )

    result = []
    for category in categories:
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
            for tag in category.tags.all()
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
    response={201: TagWithCategoryResponse, 400: Error, 401: Error},
    auth=auth,
    tags=["Tags"],
)
def suggest_tag(
    request: HttpRequest, payload: TagSuggestRequest
) -> tuple[int, dict[str, Any]]:
    """Suggest a new tag (creates with status=pending, immediately usable)."""
    # Validate category exists and is active
    category = get_object_or_404(TagCategory, id=payload.category_id, is_active=True)

    # Generate slug from name
    slug = slugify(payload.name)

    # Check if tag with same name or slug exists
    if Tag.objects.filter(name__iexact=payload.name).exists():
        return 400, {"detail": "A tag with this name already exists"}
    if Tag.objects.filter(slug=slug).exists():
        return 400, {"detail": "A tag with this slug already exists"}

    # Create the tag as pending (user-created)
    tag = Tag.objects.create(
        name=payload.name,
        slug=slug,
        description=payload.description,
        color=payload.color,
        category=category,
        status=TagStatus.PENDING,
        created_by=request.auth,
    )

    return 201, {
        "id": tag.id,
        "name": tag.name,
        "slug": tag.slug,
        "description": tag.description,
        "color": tag.color,
        "category_id": category.id,
        "category_slug": category.slug,
        "status": tag.status,
    }


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

    tags = Tag.objects.filter(status=TagStatus.PENDING).select_related("category")
    return [
        {
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "description": tag.description,
            "color": tag.color,
            "category_id": tag.category.id if tag.category else None,
            "category_slug": tag.category.slug if tag.category else None,
            "status": tag.status,
        }
        for tag in tags
    ]


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

    tag = get_object_or_404(Tag.objects.select_related("category"), id=tag_id)

    if tag.status == TagStatus.APPROVED:
        return 400, {"detail": "Tag is already approved"}
    if tag.status == TagStatus.REJECTED:
        return 400, {"detail": "Cannot approve a rejected tag"}

    tag.status = TagStatus.APPROVED
    tag.reviewed_by = request.auth
    tag.reviewed_at = timezone.now()
    tag.save()

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

    tag = get_object_or_404(Tag.objects.select_related("category"), id=tag_id)

    if tag.status == TagStatus.REJECTED:
        return 400, {"detail": "Tag is already rejected"}

    # Remove from all projects
    tag.projects.clear()

    tag.status = TagStatus.REJECTED
    tag.reviewed_by = request.auth
    tag.reviewed_at = timezone.now()
    tag.save()

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
