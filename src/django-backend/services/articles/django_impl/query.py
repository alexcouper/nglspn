from __future__ import annotations

from typing import TYPE_CHECKING

from apps.articles.models import Article, ArticleState
from services.articles.query_interface import ArticleQueryInterface

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet


class DjangoArticleQuery(ArticleQueryInterface):
    def get_by_id(self, article_id: UUID) -> Article | None:
        return (
            Article.objects.select_related("project", "channel", "author", "hero_image")
            .filter(pk=article_id)
            .first()
        )

    def get_by_project_and_slug(
        self,
        project_slug: str,
        article_slug: str,
    ) -> Article | None:
        return (
            Article.objects.select_related("project", "channel", "author", "hero_image")
            .filter(project__slug=project_slug, slug=article_slug)
            .first()
        )

    def for_project(
        self,
        project_id: UUID,
        *,
        include_drafts: bool = False,
    ) -> QuerySet[Article]:
        qs = Article.objects.filter(project_id=project_id).select_related(
            "channel", "author", "hero_image"
        )
        if not include_drafts:
            qs = qs.filter(state=ArticleState.PUBLISHED)
        return qs
