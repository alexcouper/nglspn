from uuid import UUID

from django.utils import timezone

from apps.tags.models import Tag, TagCategory, TagStatus
from services.tags.exceptions import (
    DuplicateTagNameError,
    DuplicateTagSlugError,
    TagAlreadyApprovedError,
    TagAlreadyRejectedError,
    TagCategoryNotFoundError,
    TagNotFoundError,
    TagRejectedError,
)


class DjangoTagHandler:
    def suggest(
        self,
        *,
        name: str,
        slug: str,
        description: str | None,
        color: str | None,
        category_id: UUID,
        created_by_id: UUID,
    ) -> Tag:
        try:
            TagCategory.objects.get(id=category_id, is_active=True)
        except TagCategory.DoesNotExist:
            raise TagCategoryNotFoundError from None

        if Tag.objects.filter(name__iexact=name).exists():
            raise DuplicateTagNameError

        if Tag.objects.filter(slug=slug).exists():
            raise DuplicateTagSlugError

        return Tag.objects.create(
            name=name,
            slug=slug,
            description=description,
            color=color,
            category_id=category_id,
            status=TagStatus.PENDING,
            created_by_id=created_by_id,
        )

    def approve(self, tag_id: UUID, reviewed_by_id: UUID) -> Tag:
        try:
            tag = Tag.objects.select_related("category").get(id=tag_id)
        except Tag.DoesNotExist:
            raise TagNotFoundError from None

        if tag.status == TagStatus.APPROVED:
            raise TagAlreadyApprovedError
        if tag.status == TagStatus.REJECTED:
            raise TagRejectedError

        tag.status = TagStatus.APPROVED
        tag.reviewed_by_id = reviewed_by_id
        tag.reviewed_at = timezone.now()
        tag.save()
        return tag

    def reject(self, tag_id: UUID, reviewed_by_id: UUID) -> Tag:
        try:
            tag = Tag.objects.select_related("category").get(id=tag_id)
        except Tag.DoesNotExist:
            raise TagNotFoundError from None

        if tag.status == TagStatus.REJECTED:
            raise TagAlreadyRejectedError

        tag.projects.clear()

        tag.status = TagStatus.REJECTED
        tag.reviewed_by_id = reviewed_by_id
        tag.reviewed_at = timezone.now()
        tag.save()
        return tag
