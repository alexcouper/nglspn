"""`/api/auth/me/articles`: the caller's own writing, created from the profile
and listed there in every state."""

import pytest
from hamcrest import assert_that, contains_exactly, equal_to, has_entries

from api.auth.jwt import create_access_token
from apps.articles.models import Article, ArticleGlobalVisibility
from tests.factories import (
    ArticleFactory,
    AuthorArticleFactory,
    PublishedArticleFactory,
    PublishedAuthorArticleFactory,
    UserFactory,
)

URL = "/api/auth/me/articles"


def create_own(client, headers, **payload):
    return client.post(URL, data=payload, content_type="application/json", **headers)


def listed_ids(response) -> list[str]:
    return [row["id"] for row in response.json()]


def headers_for(user) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {create_access_token(user.id)}"}


@pytest.mark.django_db
class TestCreateOwnArticle:
    def test_anonymous_is_401(self, client) -> None:
        assert_that(create_own(client, {}).status_code, equal_to(401))

    def test_creates_a_draft_owned_by_the_caller(self, client, user, auth_headers):
        response = create_own(client, auth_headers, title="Mine")

        assert_that(response.status_code, equal_to(201))
        assert_that(
            response.json(),
            has_entries(title="Mine", state="draft", project=None, channel=None),
        )
        article = Article.objects.get(id=response.json()["id"])
        assert_that(article.author_id, equal_to(user.id))

    def test_system_and_inactive_users_cannot_create_one(self, client) -> None:
        for account in (UserFactory(is_system_user=True), UserFactory(is_active=False)):
            response = create_own(client, headers_for(account))

            assert_that(response.status_code, equal_to(401))
            assert_that(
                Article.objects.filter(author=account).exists(), equal_to(False)
            )


@pytest.mark.django_db
class TestListOwnArticles:
    def test_anonymous_is_401(self, client) -> None:
        assert_that(client.get(URL).status_code, equal_to(401))

    def test_lists_every_state_of_both_kinds_with_badge_fields(
        self, client, user, auth_headers
    ) -> None:
        draft = AuthorArticleFactory(author=user)
        pending = PublishedAuthorArticleFactory(
            author=user, global_visibility=ArticleGlobalVisibility.PENDING
        )
        on_project = PublishedArticleFactory(author=user)
        AuthorArticleFactory()  # someone else's

        response = client.get(URL, **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            set(listed_ids(response)),
            equal_to({str(draft.id), str(pending.id), str(on_project.id)}),
        )
        by_id = {row["id"]: row for row in response.json()}
        assert_that(
            by_id[str(pending.id)],
            has_entries(
                state="published",
                global_visibility="pending",
                is_globally_visible=False,
                project=None,
            ),
        )
        assert_that(
            by_id[str(on_project.id)]["project"],
            has_entries(slug=on_project.project.slug),
        )

    def test_drafts_come_first(self, client, user, auth_headers) -> None:
        published = PublishedAuthorArticleFactory(author=user)
        draft = ArticleFactory(author=user)

        response = client.get(URL, **auth_headers)

        assert_that(
            listed_ids(response), contains_exactly(str(draft.id), str(published.id))
        )
