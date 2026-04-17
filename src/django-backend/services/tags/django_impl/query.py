from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Prefetch, QuerySet

from apps.projects.models import ProjectStatus
from apps.tags.models import Tag, TagCategory, TagStatus
from services.tags.exceptions import TagNotFoundError
from services.tags.query_interface import CategoryTags, TagQueryInterface

if TYPE_CHECKING:
    from uuid import UUID


class DjangoTagQuery(TagQueryInterface):
    def list_non_rejected(self) -> QuerySet[Tag]:
        return Tag.objects.exclude(status=TagStatus.REJECTED)

    def list_categories(self) -> QuerySet[TagCategory]:
        return TagCategory.objects.filter(is_active=True)

    def list_grouped(self, *, with_projects: bool = False) -> list[CategoryTags]:
        tag_queryset = Tag.objects.exclude(status=TagStatus.REJECTED)
        if with_projects:
            tag_queryset = tag_queryset.filter(projects__status=ProjectStatus.APPROVED)
        tag_queryset = tag_queryset.distinct()

        categories = TagCategory.objects.filter(is_active=True).prefetch_related(
            Prefetch("tags", queryset=tag_queryset)
        )

        return [CategoryTags(category=c, tags=list(c.tags.all())) for c in categories]

    def list_pending(self) -> QuerySet[Tag]:
        return Tag.objects.filter(status=TagStatus.PENDING).select_related("category")

    def get_by_id(self, tag_id: UUID) -> Tag:
        try:
            return Tag.objects.select_related("category").get(id=tag_id)
        except Tag.DoesNotExist:
            raise TagNotFoundError from None
