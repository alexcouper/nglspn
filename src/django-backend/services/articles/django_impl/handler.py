from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.articles.models import (
    Article,
    ArticleGlobalVisibility,
    ArticleSource,
    ArticleState,
)
from apps.articles.slugs import assign_unique_article_slug
from apps.follows.models import Channel
from apps.projects.models import ProjectImage
from services.articles.exceptions import (
    ArticleNotFoundError,
    ArticleNotPublishableError,
    ChannelHasArticlesError,
    ChannelNotFoundError,
    ChannelOnWrongProjectError,
    DuplicateChannelNameError,
    HeroImageOnWrongProjectError,
    LastChannelError,
    PublishedArticleNeedsHeroImageError,
)
from services.articles.handler_interface import (
    UNSET,
    ArticleHandlerInterface,
    UnsetType,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

logger = logging.getLogger(__name__)


def _is_backdated(published_at: datetime | None) -> bool:
    """A publish is backdated if its published_at is more than 60s in the past."""
    if published_at is None:
        return False
    return published_at < timezone.now() - timedelta(seconds=60)


def _resolve_visibility_on_publish(article: Article) -> str:
    if article.source == ArticleSource.EXTERNAL:
        # Phase 6 governance: external articles route via feed approval state,
        # not the author's trust flag (the author may not even be a User).
        # Until Phase 6 lands, this branch is unreachable from the API path.
        return ArticleGlobalVisibility.PENDING
    if article.author and article.author.article_trust:
        return ArticleGlobalVisibility.AUTO
    return ArticleGlobalVisibility.PENDING


class DjangoArticleHandler(ArticleHandlerInterface):
    # ------------------------------------------------------------------
    # Articles
    # ------------------------------------------------------------------

    def create_draft(
        self,
        *,
        project_id: UUID,
        channel_id: UUID,
        author_id: UUID,
        title: str = "",
        body: str = "",
        hero_image_id: UUID | None = None,
    ) -> Article:
        channel = self._resolve_channel_on_project(channel_id, project_id)
        hero_image = self._resolve_hero_image(hero_image_id, project_id)
        article = Article(
            project_id=project_id,
            channel=channel,
            author_id=author_id,
            title=title,
            body=body,
            hero_image=hero_image,
            source=ArticleSource.INTERNAL,
            state=ArticleState.DRAFT,
        )
        article.save()
        return article

    def update_article(
        self,
        article_id: UUID,
        *,
        title: str | None = None,
        body: str | None = None,
        summary: str | None = None,
        hero_image_id: UUID | None | UnsetType = UNSET,
        channel_id: UUID | None = None,
        published_at: datetime | None = None,
    ) -> Article:
        article = self._get_article(article_id)
        update_fields: list[str] = []

        if title is not None and title != article.title:
            article.title = title
            update_fields.append("title")
        if body is not None and body != article.body:
            article.body = body
            update_fields.append("body")
        if summary is not None and summary != article.summary:
            article.summary = summary
            update_fields.append("summary")
        if hero_image_id is not UNSET:
            # _resolve_hero_image raises for an unknown id, so None here only
            # ever means "the caller asked to clear it".
            hero_image = self._resolve_hero_image(hero_image_id, article.project_id)
            if hero_image is None and article.state == ArticleState.PUBLISHED:
                raise PublishedArticleNeedsHeroImageError
            new_hero_id = hero_image.pk if hero_image else None
            if new_hero_id != article.hero_image_id:
                article.hero_image = hero_image
                update_fields.append("hero_image")
        if channel_id is not None and channel_id != article.channel_id:
            channel = self._resolve_channel_on_project(channel_id, article.project_id)
            article.channel = channel
            update_fields.append("channel")
        if published_at is not None and published_at != article.published_at:
            # Editing published_at after publish is allowed but NEVER fires
            # retroactive notifications (per spec).
            article.published_at = published_at
            update_fields.append("published_at")

        if update_fields:
            article.save(update_fields=update_fields)
        return article

    def publish(
        self,
        article_id: UUID,
        *,
        published_at: datetime | None = None,
    ) -> Article:
        article = self._get_article(article_id)

        if not article.title or not article.body or article.hero_image_id is None:
            raise ArticleNotPublishableError

        effective_published_at = published_at or timezone.now()

        with transaction.atomic():
            article.state = ArticleState.PUBLISHED
            article.published_at = effective_published_at
            article.global_visibility = _resolve_visibility_on_publish(article)
            article.save(update_fields=["state", "published_at", "global_visibility"])
            if article.slug is None:
                assign_unique_article_slug(article)

        if not _is_backdated(effective_published_at):
            # Notification fan-out is owned by the notifications service so
            # the same trigger drives email + in-app paths consistently.
            from services import HANDLERS  # noqa: PLC0415

            HANDLERS.notifications.create_notifications_for_article(article.id)

        return article

    def delete_article(self, article_id: UUID) -> None:
        deleted, _ = Article.objects.filter(pk=article_id).delete()
        if not deleted:
            raise ArticleNotFoundError

    def set_global_visibility(self, article_id: UUID, value: str) -> Article:
        if value not in {choice.value for choice in ArticleGlobalVisibility}:
            msg = f"invalid global_visibility value: {value!r}"
            raise ValueError(msg)
        article = self._get_article(article_id)
        if article.global_visibility == value:
            return article
        article.global_visibility = value
        article.save(update_fields=["global_visibility"])
        return article

    # ------------------------------------------------------------------
    # Channels
    # ------------------------------------------------------------------

    def add_channel(self, project_id: UUID, name: str) -> Channel:
        try:
            return Channel.objects.create(project_id=project_id, name=name)
        except IntegrityError as exc:
            raise DuplicateChannelNameError from exc

    def rename_channel(self, channel_id: UUID, new_name: str) -> Channel:
        try:
            channel = Channel.objects.get(pk=channel_id)
        except Channel.DoesNotExist as exc:
            raise ChannelNotFoundError from exc
        if channel.name == new_name:
            return channel
        channel.name = new_name
        try:
            channel.save(update_fields=["name"])
        except IntegrityError as exc:
            raise DuplicateChannelNameError from exc
        return channel

    def delete_channel(self, channel_id: UUID) -> None:
        try:
            channel = Channel.objects.select_related("project").get(pk=channel_id)
        except Channel.DoesNotExist as exc:
            raise ChannelNotFoundError from exc

        article_count = Article.objects.filter(channel=channel).count()
        if article_count:
            raise ChannelHasArticlesError(article_count)

        sibling_count = Channel.objects.filter(project=channel.project).count()
        if sibling_count <= 1:
            raise LastChannelError

        channel.delete()

    def bulk_reassign_articles(
        self,
        source_channel_id: UUID,
        target_channel_id: UUID,
    ) -> int:
        try:
            source = Channel.objects.get(pk=source_channel_id)
            target = Channel.objects.get(pk=target_channel_id)
        except Channel.DoesNotExist as exc:
            raise ChannelNotFoundError from exc
        if source.project_id != target.project_id:
            raise ChannelOnWrongProjectError
        return Article.objects.filter(channel=source).update(channel=target)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_article(self, article_id: UUID) -> Article:
        try:
            return (
                Article.objects.select_related(
                    "project", "channel", "author", "hero_image"
                )
                .prefetch_related("hero_image__variants")
                .get(pk=article_id)
            )
        except Article.DoesNotExist as exc:
            raise ArticleNotFoundError from exc

    def _resolve_channel_on_project(
        self, channel_id: UUID, project_id: UUID
    ) -> Channel:
        try:
            channel = Channel.objects.get(pk=channel_id)
        except Channel.DoesNotExist as exc:
            raise ChannelNotFoundError from exc
        if channel.project_id != project_id:
            raise ChannelOnWrongProjectError
        return channel

    def _resolve_hero_image(
        self, hero_image_id: UUID | None, project_id: UUID
    ) -> ProjectImage | None:
        if hero_image_id is None:
            return None
        try:
            image = ProjectImage.objects.get(pk=hero_image_id)
        except ProjectImage.DoesNotExist as exc:
            raise HeroImageOnWrongProjectError from exc
        if image.project_id != project_id:
            raise HeroImageOnWrongProjectError
        return image
