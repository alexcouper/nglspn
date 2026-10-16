from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema

from services.articles.summary import derive_summary
from services.project.django_impl.query import resolve_image_by_purpose, variant_url

from .article import CropRect


class FeedProjectRef(Schema):
    id: UUID
    slug: str | None
    title: str
    tagline: str
    category_name: str | None
    icon_url: str | None


class FeedArticleRef(Schema):
    id: UUID
    slug: str | None
    title: str
    summary: str
    channel_name: str
    # Null for an author-owned article; the author fields are its flag then.
    project_slug: str | None
    project_title: str | None
    author_id: UUID | None
    author_name: str | None
    author_avatar_url: str | None
    listing_image_url: str | None
    listing_crop: CropRect | None


class FeedDiscussionRef(Schema):
    id: UUID
    project_slug: str | None
    project_title: str
    excerpt: str


class FeedEntryResponse(Schema):
    """One row of the feed.

    Deliberately structured rather than pre-rendered: no display copy crosses
    the wire, so the labels stay where the rest of the UI's wording lives.
    """

    id: UUID
    kind: str
    occurred_at: datetime
    is_pinned: bool
    project: FeedProjectRef | None
    article: FeedArticleRef | None
    discussion: FeedDiscussionRef | None

    @staticmethod
    def resolve_project(obj: Any) -> dict[str, Any] | None:
        return _project_ref(obj.project)

    @staticmethod
    def resolve_article(obj: Any) -> dict[str, Any] | None:
        article = obj.article
        if article is None:
            return None
        image = article.listing_image
        project = article.project
        author = article.author
        return {
            "id": article.id,
            "slug": article.slug,
            "title": article.title,
            "summary": article.summary or derive_summary(article.body),
            "channel_name": article.channel.name if article.channel else "",
            "project_slug": project.slug if project else None,
            "project_title": project.title if project else None,
            "author_id": author.id if author else None,
            "author_name": author.full_name if author else None,
            "author_avatar_url": author.avatar_url if author else None,
            "listing_image_url": image.url if image is not None else None,
            "listing_crop": article.listing_crop,
        }

    @staticmethod
    def resolve_discussion(obj: Any) -> dict[str, Any] | None:
        discussion = obj.discussion
        if discussion is None:
            return None
        return {
            "id": discussion.id,
            "project_slug": discussion.project.slug,
            "project_title": discussion.project.title,
            "excerpt": derive_summary(discussion.body),
        }


class FeedPageResponse(Schema):
    entries: list[FeedEntryResponse]
    # Pass back as `before` to fetch the next page, untouched. Null when the
    # stream is exhausted. Opaque: it encodes the position of the last entry,
    # not a time to filter on.
    next_cursor: str | None
    lead: FeedEntryResponse | None


def _project_ref(project: Any) -> dict[str, Any] | None:
    if project is None:
        return None
    return {
        "id": project.id,
        "slug": project.slug,
        "title": project.title,
        "tagline": project.tagline,
        "category_name": project.category.name if project.category else None,
        # Same resolution and size Discover's cards use, so a project looks the
        # same in both places. Reads the prefetched gallery — never call this
        # without FeedEvent.objects.with_sources().
        "icon_url": variant_url(resolve_image_by_purpose(project, "icon"), "thumb"),
    }
