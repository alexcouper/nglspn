from typing import Any
from uuid import UUID

from django.db.models import Prefetch, QuerySet

from apps.projects.models import ProjectStatus
from apps.tags.models import Tag, TagCategory, TagStatus
from services.tags.exceptions import TagNotFoundError
from services.tags.query_interface import TagQueryInterface


class DjangoTagQuery(TagQueryInterface):
    def list_non_rejected(self) -> QuerySet[Tag]:
        return Tag.objects.exclude(status=TagStatus.REJECTED)

    def list_categories(self) -> QuerySet[TagCategory]:
        return TagCategory.objects.filter(is_active=True)

    def list_grouped(self, *, with_projects: bool = False) -> list[dict[str, Any]]:
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

    def list_pending(self) -> QuerySet[Tag]:
        return Tag.objects.filter(status=TagStatus.PENDING).select_related("category")

    def get_by_id(self, tag_id: UUID) -> Tag:
        try:
            return Tag.objects.select_related("category").get(id=tag_id)
        except Tag.DoesNotExist:
            raise TagNotFoundError from None
