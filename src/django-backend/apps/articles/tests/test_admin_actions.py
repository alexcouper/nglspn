import pytest
from django.contrib.admin.sites import AdminSite

from apps.articles.admin import ArticleAdmin
from apps.articles.models import Article, ArticleGlobalVisibility
from tests.factories import (
    ArticleFactory,
    PendingArticleFactory,
    PublishedArticleFactory,
)


class FakeRequest:
    """The actions only reach the request through message_user, which is stubbed."""


def article_admin() -> ArticleAdmin:
    admin = ArticleAdmin(Article, AdminSite())
    admin.message_user = lambda *args, **kwargs: None
    return admin


def selection(*articles) -> "Article":
    return Article.objects.filter(pk__in=[a.pk for a in articles])


@pytest.mark.django_db
class TestVisibilityActions:
    """The actions are the only way in: the form cannot edit visibility.

    Approving is what notifies an article's followers and stamps `approved_at`,
    and a ModelAdmin form saves the row directly — so going through the handler
    is the whole point of these existing.
    """

    def test_approving_makes_the_article_visible(self):
        article = PendingArticleFactory()

        article_admin().approve_articles(FakeRequest(), selection(article))

        article.refresh_from_db()
        assert article.global_visibility == ArticleGlobalVisibility.APPROVED
        assert article.is_globally_visible is True

    def test_approving_stamps_the_approval_time(self):
        article = PendingArticleFactory()
        assert article.approved_at is None

        article_admin().approve_articles(FakeRequest(), selection(article))

        article.refresh_from_db()
        assert article.approved_at is not None

    def test_demoting_hides_the_article(self):
        article = PublishedArticleFactory()

        article_admin().demote_articles(FakeRequest(), selection(article))

        article.refresh_from_db()
        assert article.global_visibility == ArticleGlobalVisibility.DEMOTED
        assert article.is_globally_visible is False

    def test_approving_several_at_once(self):
        articles = [PendingArticleFactory() for _ in range(3)]

        article_admin().approve_articles(FakeRequest(), selection(*articles))

        for article in articles:
            article.refresh_from_db()
            assert article.is_globally_visible is True

    def test_approving_an_already_approved_article_changes_nothing(self):
        article = PublishedArticleFactory(
            global_visibility=ArticleGlobalVisibility.APPROVED
        )
        article_admin().approve_articles(FakeRequest(), selection(article))
        article.refresh_from_db()
        first_approval = article.approved_at

        article_admin().approve_articles(FakeRequest(), selection(article))

        article.refresh_from_db()
        assert article.approved_at == first_approval

    def test_visibility_cannot_be_typed_into_the_form(self):
        """A form save bypasses the handler, so the field is read-only."""
        readonly = article_admin().get_readonly_fields(FakeRequest())

        assert "global_visibility" in readonly
        assert "approved_at" in readonly


@pytest.mark.django_db
class TestApprovingADraft:
    def test_a_draft_stays_invisible_and_unstamped(self):
        """Visibility is settable early; it means nothing until the article
        publishes, and publish does its own stamping.
        """
        article = ArticleFactory()

        article_admin().approve_articles(FakeRequest(), selection(article))

        article.refresh_from_db()
        assert article.is_globally_visible is False
        assert article.approved_at is None
