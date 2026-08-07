from __future__ import annotations

import pytest

from apps.articles.models import ArticleState
from apps.articles.slugs import (
    assign_unique_article_slug,
    project_has_article_with_slug,
)
from tests.factories import ArticleFactory, ProjectFactory


def _publishable_draft(project, title):
    """A draft with the right shape to receive a slug — Article publishing
    flows assign the slug only after the title is set, so the unit tests
    construct rows directly here rather than going through the handler.
    """
    return ArticleFactory(
        project=project, title=title, state=ArticleState.DRAFT, slug=None
    )


@pytest.mark.django_db
class TestAssignUniqueArticleSlug:
    def test_icelandic_title_is_transliterated(self):
        article = _publishable_draft(ProjectFactory(), "Súperþing")

        assign_unique_article_slug(article)

        article.refresh_from_db()
        assert article.slug == "superthing"

    def test_punctuation_becomes_dashes(self):
        article = _publishable_draft(ProjectFactory(), "foo.com/news?x=1")

        assign_unique_article_slug(article)

        article.refresh_from_db()
        assert article.slug == "foo-com-news-x-1"

    def test_empty_title_falls_back_to_article(self):
        article = _publishable_draft(ProjectFactory(), "")

        assign_unique_article_slug(article)

        article.refresh_from_db()
        assert article.slug == "article"


@pytest.mark.django_db
class TestSlugCollisionSuffix:
    def test_walks_past_multiple_collisions(self):
        project = ProjectFactory()
        for slug in ("news", "news-2", "news-3"):
            ArticleFactory(
                project=project,
                title=slug,
                slug=slug,
                state=ArticleState.PUBLISHED,
            )
        article = _publishable_draft(project, "News")

        assign_unique_article_slug(article)

        article.refresh_from_db()
        assert article.slug == "news-4"


@pytest.mark.django_db
class TestProjectHasArticleWithSlug:
    def test_returns_true_when_present(self):
        project = ProjectFactory()
        ArticleFactory(
            project=project,
            slug="my-slug",
            state=ArticleState.PUBLISHED,
        )

        assert project_has_article_with_slug(project.id, "my-slug") is True

    def test_returns_false_when_absent(self):
        project = ProjectFactory()

        assert project_has_article_with_slug(project.id, "absent") is False

    def test_scoped_to_project(self):
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        ArticleFactory(
            project=project_a,
            slug="my-slug",
            state=ArticleState.PUBLISHED,
        )

        assert project_has_article_with_slug(project_b.id, "my-slug") is False
