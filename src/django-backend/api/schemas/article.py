from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema

from services.articles.summary import derive_summary

from .project import ProjectImageResponse
from .user import PublicUserProfile


class ArticleCreate(Schema):
    channel_id: UUID
    title: str = ""
    body: str = ""
    hero_image_id: UUID | None = None


class ArticleUpdate(Schema):
    title: str | None = None
    body: str | None = None
    # "" is meaningful here: it clears the override and returns the article to
    # the derived fallback.
    summary: str | None = None
    hero_image_id: UUID | None = None
    channel_id: UUID | None = None
    published_at: datetime | None = None


class ArticlePublish(Schema):
    published_at: datetime | None = None


class ArticleProjectRef(Schema):
    id: UUID
    slug: str | None
    title: str


class ArticleChannelRef(Schema):
    id: UUID
    name: str


class ArticleOut(Schema):
    id: UUID
    project: ArticleProjectRef
    channel: ArticleChannelRef
    author: PublicUserProfile | None
    title: str
    body: str
    # `summary` is the stored override (so the editor knows whether one exists);
    # `summary_display` is what a listing will actually show.
    summary: str
    summary_display: str
    hero_image_id: UUID | None
    hero_image_url: str | None
    # The full image, with variants. The editor needs this: article images are
    # excluded from `ProjectResponse.images`, so it cannot look the hero up
    # there when loading an article for editing.
    hero_image: ProjectImageResponse | None
    slug: str | None
    source: str
    external_url: str | None
    state: str
    published_at: datetime | None
    global_visibility: str
    is_globally_visible: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_project(obj: Any) -> dict[str, Any]:
        project = obj.project
        return {"id": project.id, "slug": project.slug, "title": project.title}

    @staticmethod
    def resolve_channel(obj: Any) -> dict[str, Any]:
        channel = obj.channel
        return {"id": channel.id, "name": channel.name}

    @staticmethod
    def resolve_summary_display(obj: Any) -> str:
        return obj.summary or derive_summary(obj.body)

    @staticmethod
    def resolve_hero_image_id(obj: Any) -> UUID | None:
        return obj.hero_image_id

    @staticmethod
    def resolve_hero_image_url(obj: Any) -> str | None:
        hero = obj.hero_image
        if hero is None:
            return None
        return hero.url

    @staticmethod
    def resolve_hero_image(obj: Any) -> Any:
        return obj.hero_image

    @staticmethod
    def resolve_is_globally_visible(obj: Any) -> bool:
        return obj.is_globally_visible


class ArticleListItem(Schema):
    id: UUID
    title: str
    summary: str
    slug: str | None
    state: str
    published_at: datetime | None
    global_visibility: str
    channel: ArticleChannelRef
    hero_image_url: str | None

    @staticmethod
    def resolve_channel(obj: Any) -> dict[str, Any]:
        channel = obj.channel
        return {"id": channel.id, "name": channel.name}

    # REPO.articles.for_project selects whole rows, so obj.body is already
    # loaded and this costs no extra queries. Do not add .only(...) to that
    # queryset without including body.
    @staticmethod
    def resolve_summary(obj: Any) -> str:
        return obj.summary or derive_summary(obj.body)

    @staticmethod
    def resolve_hero_image_url(obj: Any) -> str | None:
        hero = obj.hero_image
        if hero is None:
            return None
        return hero.url
