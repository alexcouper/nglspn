from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema

from .user import PublicUserProfile


class ArticleCreate(Schema):
    channel_id: UUID
    title: str = ""
    body: str = ""
    hero_image_id: UUID | None = None


class ArticleUpdate(Schema):
    title: str | None = None
    body: str | None = None
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
    hero_image_id: UUID | None
    hero_image_url: str | None
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
    def resolve_hero_image_id(obj: Any) -> UUID | None:
        return obj.hero_image_id

    @staticmethod
    def resolve_hero_image_url(obj: Any) -> str | None:
        hero = obj.hero_image
        if hero is None:
            return None
        return hero.url

    @staticmethod
    def resolve_is_globally_visible(obj: Any) -> bool:
        return obj.is_globally_visible


class ChannelCreate(Schema):
    name: str


class ChannelRename(Schema):
    name: str


class ChannelReassign(Schema):
    target_channel_id: UUID


class ChannelResponse(Schema):
    id: UUID
    name: str


class ChannelReassignResponse(Schema):
    reassigned: int


class ChannelConflictResponse(Schema):
    detail: str
    article_count: int | None = None


class ArticleListItem(Schema):
    id: UUID
    title: str
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

    @staticmethod
    def resolve_hero_image_url(obj: Any) -> str | None:
        hero = obj.hero_image
        if hero is None:
            return None
        return hero.url
