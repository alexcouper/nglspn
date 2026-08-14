from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.articles.models import (
    Article,
    ArticleGlobalVisibility,
    ArticleSource,
    ArticleState,
)
from tests.factories import ArticleFactory, ProjectFactory


@pytest.mark.django_db
class TestSourceExternalUrlGuard:
    """The save guard mirrors the DB CHECK so SQLite test runs catch it too."""

    def test_internal_with_external_url_raises(self):
        article = ArticleFactory.build(
            project=ProjectFactory(),
            source=ArticleSource.INTERNAL,
            external_url="https://example.com/news",
        )

        with pytest.raises(ValidationError, match="external_url"):
            article.save()

    def test_external_without_external_url_raises(self):
        article = ArticleFactory.build(
            project=ProjectFactory(),
            source=ArticleSource.EXTERNAL,
            external_url=None,
        )

        with pytest.raises(ValidationError, match="external_url"):
            article.save()

    def test_internal_without_external_url_saves(self):
        article = ArticleFactory(
            source=ArticleSource.INTERNAL,
            external_url=None,
        )

        assert article.pk is not None

    def test_external_with_external_url_saves(self):
        article = ArticleFactory(
            source=ArticleSource.EXTERNAL,
            external_url="https://example.com/news",
        )

        assert article.pk is not None


@pytest.mark.django_db
class TestSlugUniquenessConstraint:
    def test_two_articles_in_same_project_cannot_share_a_slug(self):
        project = ProjectFactory()
        ArticleFactory(project=project, slug="my-slug", state=ArticleState.PUBLISHED)

        dup = ArticleFactory.build(
            project=project, slug="my-slug", state=ArticleState.PUBLISHED
        )

        with pytest.raises(IntegrityError):
            dup.save()

    def test_two_articles_in_different_projects_may_share_a_slug(self):
        a = ArticleFactory(slug="my-slug", state=ArticleState.PUBLISHED)
        b = ArticleFactory(slug="my-slug", state=ArticleState.PUBLISHED)

        assert a.project_id != b.project_id
        assert a.slug == b.slug

    def test_many_articles_in_one_project_may_have_null_slug(self):
        """The partial unique constraint is scoped to WHERE slug IS NOT NULL,
        so draft rows (slug=None) coexist freely.
        """
        project = ProjectFactory()
        ArticleFactory(project=project, slug=None)
        ArticleFactory(project=project, slug=None)

        assert Article.objects.filter(project=project, slug__isnull=True).count() == 2


@pytest.mark.django_db
class TestIsGloballyVisibleProperty:
    """The four published-state combinations are covered as side assertions
    in services/articles/django_impl/test_handler.py (trusted/untrusted
    publish + admin approve/demote). The draft case is the missing wrinkle:
    state must be PUBLISHED regardless of global_visibility.
    """

    def test_draft_is_never_globally_visible(self):
        article = ArticleFactory(
            state=ArticleState.DRAFT,
            global_visibility=ArticleGlobalVisibility.AUTO,
        )

        assert article.is_globally_visible is False


@pytest.mark.django_db
class TestVisibilityRuleIsSpelledTheSameTwice:
    """The rule exists as a Python predicate and as a queryset condition.

    Neither can be derived from the other cheaply: ``Q.check()`` compiles and
    executes SQL, and the property is read per row while serialising a feed
    page. So the two spellings share only ``GLOBALLY_VISIBLE_STATES``, and this
    exhausts the state space to catch the day they disagree.
    """

    @pytest.mark.parametrize("visibility", ArticleGlobalVisibility.values)
    @pytest.mark.parametrize("state", ArticleState.values)
    def test_property_and_queryset_agree(self, state: str, visibility: str):
        article = ArticleFactory(state=state, global_visibility=visibility)

        in_queryset = Article.objects.globally_visible().filter(pk=article.pk).exists()

        assert article.is_globally_visible == in_queryset
