"""An author-owned article fans out through the author's personal channel, and
through nothing else."""

from __future__ import annotations

import logging

import pytest

from apps.notifications.models import Notification
from services import HANDLERS
from services.notifications.django_impl.handler import DjangoNotificationHandler
from tests.factories import (
    ArticleFactory,
    AuthorArticleFactory,
    ChannelFactory,
    ProjectFactory,
    PublishedAuthorArticleFactory,
    UserFactory,
    make_followed_channel,
)


@pytest.fixture
def handler():
    return DjangoNotificationHandler()


def follow_person(follower, person) -> None:
    HANDLERS.follows.follow_user(follower.id, person)


def recipients_of(article) -> set:
    return set(
        Notification.objects.filter(article=article).values_list(
            "recipient_id", flat=True
        )
    )


@pytest.mark.django_db
class TestAuthorOwnedFanOut:
    def test_reaches_the_persons_followers_and_not_the_author(self, handler):
        author = UserFactory()
        article = PublishedAuthorArticleFactory(author=author)
        followers = [UserFactory(), UserFactory()]
        for follower in followers:
            follow_person(follower, author)

        handler.create_notifications_for_article(article.id)

        assert recipients_of(article) == {f.id for f in followers}

    def test_emits_no_house_channel_log_line(self, handler, caplog):
        author = UserFactory()
        article = PublishedAuthorArticleFactory(author=author)
        follow_person(UserFactory(), author)

        with caplog.at_level(logging.INFO):
            handler.create_notifications_for_article(article.id)

        assert not any(
            "house_channel_article_enqueued" in r.getMessage() for r in caplog.records
        )

    def test_a_project_follower_is_not_delivered_the_persons_article(self, handler):
        author = UserFactory()
        project = ProjectFactory(owner=author)
        project_follower = UserFactory()
        make_followed_channel(
            project_follower, project, ChannelFactory(project=project, name="Updates")
        )
        article = PublishedAuthorArticleFactory(author=author)

        handler.create_notifications_for_article(article.id)

        assert recipients_of(article) == set()

    def test_a_person_follower_is_not_delivered_their_project_article(self, handler):
        author = UserFactory()
        person_follower = UserFactory()
        follow_person(person_follower, author)
        project = ProjectFactory(owner=author)
        article = HANDLERS.articles.publish(
            ArticleFactory(project=project, author=author).id
        )

        handler.create_notifications_for_article(article.id)

        assert person_follower.id not in recipients_of(article)

    def test_a_follower_from_before_the_first_publish_is_delivered(self, handler):
        author = UserFactory()
        early_follower = UserFactory()
        follow_person(early_follower, author)

        article = HANDLERS.articles.publish(AuthorArticleFactory(author=author).id)

        assert recipients_of(article) == {early_follower.id}

    def test_a_draft_with_no_channel_is_a_no_op(self, handler):
        article = AuthorArticleFactory()

        handler.create_notifications_for_article(article.id)

        assert recipients_of(article) == set()


@pytest.mark.django_db
class TestAuthorOwnedGroup:
    def test_group_has_no_project_and_carries_the_author(self, handler):
        author = UserFactory(first_name="Ada", last_name="Lovelace")
        reader = UserFactory()
        article = PublishedAuthorArticleFactory(author=author, title="Hello")
        Notification.objects.create(recipient=reader, article=article)

        [group] = handler.list_unread_groups_for_user(reader.id)

        assert group.project is None
        assert (group.author.id, group.author.name) == (author.id, "Ada Lovelace")
        assert group.article_title == "Hello"

    def test_a_project_article_group_carries_both(self, handler):
        reader = UserFactory()
        article = HANDLERS.articles.publish(ArticleFactory().id)
        Notification.objects.create(recipient=reader, article=article)

        [group] = handler.list_unread_groups_for_user(reader.id)

        assert group.project.id == article.project_id
        assert group.author.id == article.author_id
