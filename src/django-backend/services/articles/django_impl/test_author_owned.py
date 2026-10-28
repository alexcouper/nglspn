"""The handler's author-owned branch: a draft with no project, published into
the author's own channel, with images that belong to the article alone."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.articles.models import Article, ArticleState
from apps.follows.models import PERSONAL_CHANNEL_NAME, Channel
from services.articles.django_impl.handler import DjangoArticleHandler
from services.articles.exceptions import (
    LastChannelError,
    ListingImageOnWrongProjectError,
    NoChannelForAuthorArticleError,
)
from tests.factories import (
    ArticleFactory,
    AuthorArticleFactory,
    ChannelFactory,
    ProjectFactory,
    UserFactory,
    article_image,
    personal_channel,
)


@pytest.fixture
def handler():
    return DjangoArticleHandler()


def personal_channels_of(user) -> list[Channel]:
    return list(Channel.objects.filter(owner=user))


@pytest.mark.django_db
class TestCreateAuthorOwnedDraft:
    def test_draft_has_author_and_neither_project_nor_channel(self, handler):
        author = UserFactory()

        article = handler.create_draft(author_id=author.id)

        assert article.is_author_owned
        assert article.author_id == author.id
        assert article.channel_id is None
        assert article.state == ArticleState.DRAFT

    def test_creating_the_draft_creates_no_channel(self, handler):
        author = UserFactory()

        handler.create_draft(author_id=author.id)

        assert personal_channels_of(author) == []

    def test_a_project_without_a_channel_is_a_caller_error(self, handler):
        project = ProjectFactory()

        with pytest.raises(ValueError, match="channel"):
            handler.create_draft(author_id=project.creator_id, project_id=project.id)

    def test_a_channel_without_a_project_is_a_caller_error(self, handler):
        channel = ChannelFactory()

        with pytest.raises(ValueError, match="channel"):
            handler.create_draft(author_id=UserFactory().id, channel_id=channel.id)


@pytest.mark.django_db
class TestUpdateAuthorOwnedArticle:
    def test_channel_cannot_be_set(self, handler):
        article = AuthorArticleFactory()
        project_channel = ChannelFactory()

        with pytest.raises(NoChannelForAuthorArticleError):
            handler.update_article(article.id, channel_id=project_channel.id)

    def test_other_fields_update_as_usual(self, handler):
        article = AuthorArticleFactory()

        updated = handler.update_article(article.id, title="New", body="Body")

        assert (updated.title, updated.body) == ("New", "Body")


@pytest.mark.django_db
class TestPublishAuthorOwnedArticle:
    def test_first_publish_creates_the_personal_channel_and_attaches_it(self, handler):
        author = UserFactory()
        article = AuthorArticleFactory(author=author)

        published = handler.publish(article.id)

        [channel] = personal_channels_of(author)
        assert channel.name == PERSONAL_CHANNEL_NAME
        assert published.channel_id == channel.id
        assert published.state == ArticleState.PUBLISHED
        assert published.slug == "hello-world"

    def test_second_publish_reuses_the_channel(self, handler):
        author = UserFactory()
        first = handler.publish(AuthorArticleFactory(author=author).id)

        second = handler.publish(AuthorArticleFactory(author=author).id)

        assert len(personal_channels_of(author)) == 1
        assert second.channel_id == first.channel_id

    def test_slug_is_scoped_to_the_author(self, handler):
        author = UserFactory()
        handler.publish(AuthorArticleFactory(author=author, title="News").id)

        again = handler.publish(AuthorArticleFactory(author=author, title="News").id)

        assert again.slug == "news-2"

    def test_publish_fans_out_through_the_personal_channel(self, handler):
        author = UserFactory()
        article = AuthorArticleFactory(author=author)

        with patch("api.tasks.notifications.create_article_notifications") as fan_out:
            handler.publish(article.id)

        fan_out.enqueue.assert_called_once_with(str(article.id))

    def test_publishing_a_project_article_creates_no_personal_channel(self, handler):
        article = ArticleFactory()

        handler.publish(article.id)

        assert personal_channels_of(article.author) == []


@pytest.mark.django_db
class TestAuthorOwnedListingImage:
    def test_accepts_the_articles_own_image(self, handler):
        article = AuthorArticleFactory()
        own = article_image(article)

        updated = handler.update_article(article.id, listing_image_id=own.id)

        assert updated.listing_image_id == own.id

    def test_rejects_another_articles_image(self, handler):
        article = AuthorArticleFactory()
        other = article_image(AuthorArticleFactory(author=article.author))

        with pytest.raises(ListingImageOnWrongProjectError):
            handler.update_article(article.id, listing_image_id=other.id)

    def test_rejects_a_project_gallery_image(self, handler):
        article = AuthorArticleFactory()
        project = ProjectFactory(owner=article.author)
        gallery = article_image(ArticleFactory(project=project))

        with pytest.raises(ListingImageOnWrongProjectError):
            handler.update_article(article.id, listing_image_id=gallery.id)


@pytest.mark.django_db
class TestPersonalChannelIsNotManaged:
    def test_a_persons_only_channel_cannot_be_deleted(self, handler):
        channel = personal_channel(UserFactory())

        with pytest.raises(LastChannelError):
            handler.delete_channel(channel.id)

    def test_deleting_an_author_owned_article_leaves_the_channel(self, handler):
        author = UserFactory()
        article = handler.publish(AuthorArticleFactory(author=author).id)

        handler.delete_article(article.id)

        assert not Article.objects.filter(pk=article.pk).exists()
        assert len(personal_channels_of(author)) == 1
