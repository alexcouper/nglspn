from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils import timezone
from django.utils.text import slugify

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
from services.tags.handler_interface import TagHandlerInterface

if TYPE_CHECKING:
    from uuid import UUID

    from apps.users.models import User


class DjangoTagHandler(TagHandlerInterface):
    def suggest(
        self,
        *,
        name: str,
        description: str | None,
        color: str | None,
        category_id: UUID,
        created_by: User,
    ) -> Tag:
        try:
            category = TagCategory.objects.get(id=category_id, is_active=True)
        except TagCategory.DoesNotExist:
            raise TagCategoryNotFoundError from None

        if Tag.objects.filter(name__iexact=name).exists():
            raise DuplicateTagNameError

        slug = slugify(name)
        if Tag.objects.filter(slug=slug).exists():
            raise DuplicateTagSlugError

        return Tag.objects.create(
            name=name,
            slug=slug,
            description=description,
            color=color,
            category=category,
            status=TagStatus.PENDING,
            created_by=created_by,
        )

    def approve(self, tag_id: UUID, reviewed_by: User) -> Tag:
        try:
            tag = Tag.objects.select_related("category").get(id=tag_id)
        except Tag.DoesNotExist:
            raise TagNotFoundError from None

        if tag.status == TagStatus.APPROVED:
            raise TagAlreadyApprovedError
        if tag.status == TagStatus.REJECTED:
            raise TagRejectedError

        tag.status = TagStatus.APPROVED
        tag.reviewed_by = reviewed_by
        tag.reviewed_at = timezone.now()
        tag.save()
        return tag

    def reject(self, tag_id: UUID, reviewed_by: User) -> Tag:
        try:
            tag = Tag.objects.select_related("category").get(id=tag_id)
        except Tag.DoesNotExist:
            raise TagNotFoundError from None

        if tag.status == TagStatus.REJECTED:
            raise TagAlreadyRejectedError

        tag.projects.clear()
        tag.status = TagStatus.REJECTED
        tag.reviewed_by = reviewed_by
        tag.reviewed_at = timezone.now()
        tag.save()
        return tag
