"""An author-owned article's feed entry stands on the article's own visibility."""

import pytest

from apps.articles.models import ArticleGlobalVisibility
from apps.feed.models import FeedEvent
from services import HANDLERS
from tests.factories import AuthorArticleFactory, UserFactory


def renderable_article_ids() -> set:
    return set(
        FeedEvent.objects.renderable()
        .filter(article__isnull=False)
        .values_list("article_id", flat=True)
    )


@pytest.mark.django_db
class TestAuthorOwnedEntry:
    def test_publishing_appends_an_entry_that_renders(self):
        article = HANDLERS.articles.publish(AuthorArticleFactory().id)

        assert renderable_article_ids() == {article.id}

    def test_demoting_withdraws_it(self):
        article = HANDLERS.articles.publish(AuthorArticleFactory().id)

        HANDLERS.articles.set_global_visibility(
            article.id, ArticleGlobalVisibility.DEMOTED
        )

        assert renderable_article_ids() == set()

    def test_an_untrusted_authors_article_waits_for_approval(self):
        author = UserFactory(article_trust=False)
        article = HANDLERS.articles.publish(AuthorArticleFactory(author=author).id)

        assert renderable_article_ids() == set()
        HANDLERS.articles.set_global_visibility(
            article.id, ArticleGlobalVisibility.APPROVED
        )
        assert renderable_article_ids() == {article.id}

    def test_with_sources_loads_the_author_for_the_flag(self):
        article = HANDLERS.articles.publish(AuthorArticleFactory().id)

        [event] = FeedEvent.objects.renderable().with_sources()

        assert event.article.author.full_name == article.author.full_name
