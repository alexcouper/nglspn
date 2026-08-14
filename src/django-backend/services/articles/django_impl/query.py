from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import F

from apps.articles.models import Article
from apps.follows.models import Channel
from services.articles.query_interface import ArticleQueryInterface

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet


def article_detail_queryset() -> QuerySet[Article]:
    """Everything `ArticleOut` reads, without a query per figure.

    `images` is the listing-image wizard's selection list on `ArticleOut`, and
    each of those serialises its variants — so an article with N figures costs
    1 + N extra queries to serialise without this. Used by the read path and by
    the write handler's re-read, because `PATCH` and `publish` return
    `ArticleOut` too and a second prefetch list would drift from this one.
    """
    return Article.objects.select_related(
        "project", "channel", "author", "listing_image"
    ).prefetch_related("listing_image__variants", "images__variants")


class DjangoArticleQuery(ArticleQueryInterface):
    def get_by_id(self, article_id: UUID) -> Article | None:
        return article_detail_queryset().filter(pk=article_id).first()

    def get_by_project_and_slug(
        self,
        project_slug: str,
        article_slug: str,
    ) -> Article | None:
        return (
            article_detail_queryset()
            .filter(project__slug=project_slug, slug=article_slug)
            .first()
        )

    def for_project(
        self,
        project_id: UUID,
        *,
        include_hidden: bool = False,
    ) -> QuerySet[Article]:
        qs = (
            Article.objects.filter(project_id=project_id)
            .select_related("channel", "author", "listing_image")
            .order_by(F("published_at").desc(nulls_first=True), "-created_at")
        )
        if not include_hidden:
            qs = qs.globally_visible()
        return qs

    def list_channels_for_project(self, project_id: UUID) -> QuerySet[Channel]:
        return Channel.objects.filter(project_id=project_id).order_by("name")

    def get_channel_in_project(
        self, project_id: UUID, channel_id: UUID
    ) -> Channel | None:
        return Channel.objects.filter(project_id=project_id, pk=channel_id).first()
