"""Every admin changelist that prints a project tolerates an author-owned
article, a personal channel and a follow of a person."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from hamcrest import assert_that, contains_string, equal_to

from services import HANDLERS
from tests.factories import (
    AuthorArticleFactory,
    NotificationFactory,
    UserFactory,
    article_image,
    follow_user,
)


@pytest.fixture
def admin_client() -> Client:
    client = Client()
    client.force_login(UserFactory(is_staff=True, is_superuser=True))
    return client


@pytest.fixture
def seeded():
    """A published author-owned article with an image, a follower of its
    author, and an unsent notification about it."""
    author = UserFactory(first_name="Ada", last_name="Lovelace")
    article = HANDLERS.articles.publish(
        AuthorArticleFactory(author=author, title="Lab notes").id
    )
    article_image(article)
    follow_user(UserFactory(), author)
    NotificationFactory(
        recipient=UserFactory(), discussion=None, article=article, email_sent=False
    )
    return article


def assert_changelist_renders(client, url_name: str, *expected: str) -> None:
    response = client.get(reverse(url_name))
    assert_that(response.status_code, equal_to(200))
    for text in expected:
        assert_that(response.content.decode(), contains_string(text))


@pytest.mark.django_db
class TestChangelistsWithAuthorOwnedRows:
    def test_articles(self, admin_client, seeded):
        assert_changelist_renders(
            admin_client, "admin:articles_article_changelist", "Lab notes"
        )

    def test_article_change_form_links_the_author_url(self, admin_client, seeded):
        response = admin_client.get(
            reverse("admin:articles_article_change", args=[seeded.pk])
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.content.decode(),
            contains_string(f"/users/{seeded.author_id}/articles/{seeded.slug}"),
        )

    def test_channels(self, admin_client, seeded):
        assert_changelist_renders(
            admin_client, "admin:follows_channel_changelist", "Articles"
        )

    def test_follows(self, admin_client, seeded):
        assert_changelist_renders(admin_client, "admin:follows_follow_changelist")

    def test_images(self, admin_client, seeded):
        assert_changelist_renders(
            admin_client, "admin:projects_image_changelist", "Lab notes"
        )

    def test_digest_preview_keys_on_the_author(self, admin_client, seeded):
        assert_changelist_renders(
            admin_client,
            "admin:notifications_notification_preview_digest",
            "Ada Lovelace",
        )
