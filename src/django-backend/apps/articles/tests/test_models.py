from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.articles.models import (
    Article,
    ArticleGlobalVisibility,
    ArticleSource,
    ArticleState,
)
from apps.follows.models import Channel
from apps.notifications.models import Notification
from apps.projects.models import Image, OrphanedStorageObject
from tests.factories import (
    ArticleFactory,
    AuthorArticleFactory,
    ChannelFactory,
    NotificationFactory,
    ProjectFactory,
    PublishedAuthorArticleFactory,
    UserFactory,
    article_image,
    personal_channel,
)


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


@pytest.mark.django_db
class TestAuthorOwnedArticleShape:
    def test_project_article_without_a_channel_is_rejected(self):
        with pytest.raises(IntegrityError):
            ArticleFactory(channel=None)

    def test_article_with_neither_project_nor_author_is_rejected(self):
        with pytest.raises(IntegrityError):
            AuthorArticleFactory(author=None)

    def test_author_owned_draft_has_no_channel(self):
        article = AuthorArticleFactory()

        assert article.is_author_owned
        assert article.channel_id is None

    def test_author_owned_article_cannot_sit_in_a_projects_channel(self):
        project_channel = ChannelFactory(project=ProjectFactory(), name="Updates")

        with pytest.raises(ValidationError, match="channel"):
            AuthorArticleFactory(channel=project_channel)

    def test_author_owned_article_takes_its_authors_channel(self):
        author = UserFactory()

        article = AuthorArticleFactory(author=author, channel=personal_channel(author))

        assert article.channel.owner_id == author.id

    def test_str_names_the_author_when_there_is_no_project(self):
        author = UserFactory()

        article = AuthorArticleFactory(author=author, title="Hello")

        assert str(article) == f"{author}: Hello"


@pytest.mark.django_db
class TestAuthorSlugUniquenessConstraint:
    def test_same_author_cannot_reuse_a_slug_on_author_owned_articles(self):
        author = UserFactory()
        AuthorArticleFactory(author=author, slug="hello", state=ArticleState.PUBLISHED)

        with pytest.raises(IntegrityError):
            AuthorArticleFactory(
                author=author, slug="hello", state=ArticleState.PUBLISHED
            )

    def test_two_authors_may_share_a_slug(self):
        a = AuthorArticleFactory(slug="hello", state=ArticleState.PUBLISHED)
        b = AuthorArticleFactory(slug="hello", state=ArticleState.PUBLISHED)

        assert a.author_id != b.author_id

    def test_author_slug_does_not_collide_with_the_authors_project_article(self):
        author = UserFactory()
        project = ProjectFactory(owner=author)
        ArticleFactory(project=project, author=author, slug="hello")

        article = AuthorArticleFactory(author=author, slug="hello")

        assert article.pk is not None


@pytest.mark.django_db
class TestDeletingTheAuthor:
    def test_takes_author_owned_articles_and_leaves_project_ones(self):
        author = UserFactory()
        owned = AuthorArticleFactory(author=author)
        # Someone else's project: a creator is protected from deletion anyway.
        on_project = ArticleFactory(author=author)

        author.delete()

        assert not Article.objects.filter(pk=owned.pk).exists()
        on_project.refresh_from_db()
        assert on_project.author is None

    def test_takes_published_author_owned_articles_with_their_channel(self):
        author = UserFactory()
        published = PublishedAuthorArticleFactory(author=author)
        channel_id = published.channel_id

        author.delete()

        assert not Article.objects.filter(pk=published.pk).exists()
        assert not Channel.objects.filter(pk=channel_id).exists()

    def test_takes_the_articles_images_and_notifications(self):
        author = UserFactory()
        article = PublishedAuthorArticleFactory(author=author)
        image = article_image(article)
        notification = NotificationFactory(discussion=None, article=article)

        author.delete()

        assert not Image.objects.filter(pk=image.pk).exists()
        assert not Notification.objects.filter(pk=notification.pk).exists()
        assert OrphanedStorageObject.objects.filter(
            storage_key=image.storage_key
        ).exists()

    def test_a_projects_channel_with_articles_is_still_protected(self):
        article = ArticleFactory()

        with pytest.raises(ProtectedError):
            article.channel.delete()
