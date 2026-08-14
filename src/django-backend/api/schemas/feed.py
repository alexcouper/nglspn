from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema

from services.articles.summary import derive_summary

from .article import CropRect


class FeedProjectRef(Schema):
    id: UUID
    slug: str | None
    title: str
    tagline: str
    category_name: str | None


class FeedCompetitionRef(Schema):
    id: UUID
    slug: str
    name: str
    winner_slug: str | None


class FeedArticleRef(Schema):
    id: UUID
    slug: str | None
    title: str
    summary: str
    channel_name: str
    project_slug: str | None
    project_title: str
    listing_image_url: str | None
    listing_crop: CropRect | None


class FeedDiscussionRef(Schema):
    id: UUID
    project_slug: str | None
    project_title: str
    excerpt: str


class FeedSupersededRef(Schema):
    """What the entry took the place of.

    Carries the flag an article-led entry renders above its headline: a winner
    write-up still reads as a competition winner, because that is what gives it
    its context.
    """

    kind: str
    competition: FeedCompetitionRef | None
    project: FeedProjectRef | None


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
    competition: FeedCompetitionRef | None
    article: FeedArticleRef | None
    discussion: FeedDiscussionRef | None
    supersedes: FeedSupersededRef | None

    @staticmethod
    def resolve_project(obj: Any) -> dict[str, Any] | None:
        return _project_ref(obj.project)

    @staticmethod
    def resolve_competition(obj: Any) -> dict[str, Any] | None:
        return _competition_ref(obj.competition)

    @staticmethod
    def resolve_article(obj: Any) -> dict[str, Any] | None:
        article = obj.article
        if article is None:
            return None
        image = article.listing_image
        return {
            "id": article.id,
            "slug": article.slug,
            "title": article.title,
            "summary": article.summary or derive_summary(article.body),
            "channel_name": article.channel.name,
            "project_slug": article.project.slug,
            "project_title": article.project.title,
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

    @staticmethod
    def resolve_supersedes(obj: Any) -> dict[str, Any] | None:
        # Prefetched by REPO.feed — do not read this without with_sources().
        superseded = next(iter(obj.supersedes.all()), None)
        if superseded is None:
            return None
        return {
            "kind": superseded.kind,
            "competition": _competition_ref(superseded.competition),
            "project": _project_ref(superseded.project),
        }


class FeedPageResponse(Schema):
    entries: list[FeedEntryResponse]
    # Pass back as `before` to fetch the next page. Null when the stream is
    # exhausted. The cursor is an event time, which never moves once written.
    next_cursor: datetime | None
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
    }


def _competition_ref(competition: Any) -> dict[str, Any] | None:
    if competition is None:
        return None
    winner = competition.winner
    return {
        "id": competition.id,
        "slug": competition.slug,
        "name": competition.name,
        "winner_slug": winner.slug if winner is not None else None,
    }
