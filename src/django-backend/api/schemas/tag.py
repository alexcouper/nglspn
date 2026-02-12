from typing import Any
from uuid import UUID

from ninja import Schema


class TagCreate(Schema):
    name: str
    slug: str
    description: str | None = None
    color: str | None = None


class TagResponse(Schema):
    id: UUID
    name: str
    slug: str
    description: str | None
    color: str | None


class TagCategoryResponse(Schema):
    id: UUID
    name: str
    slug: str
    description: str
    display_order: int


class TagWithCategoryResponse(Schema):
    id: UUID
    name: str
    slug: str
    description: str | None
    color: str | None
    category_id: UUID | None
    category_slug: str | None
    status: str

    @staticmethod
    def resolve_category_slug(obj: Any) -> str | None:
        if hasattr(obj, "category") and obj.category:
            return obj.category.slug
        return None


class TagGroupedResponse(Schema):
    category: TagCategoryResponse
    tags: list[TagWithCategoryResponse]


class TagSuggestRequest(Schema):
    name: str
    category_id: UUID
    description: str | None = None
    color: str | None = None
