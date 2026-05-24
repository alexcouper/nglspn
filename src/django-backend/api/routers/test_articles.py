from pathlib import Path

import pytest
from hamcrest import assert_that, equal_to, has_entries, has_length

from apps.articles.models import Article, ArticleState
from tests.factories import (
    ArticleFactory,
    ChannelFactory,
    ProjectFactory,
    ProjectImageFactory,
    PublishedArticleFactory,
)


def _post(client, url, payload, headers=None):
    return client.post(
        url,
        data=payload,
        content_type="application/json",
        **(headers or {}),
    )


def _patch(client, url, payload, headers=None):
    return client.patch(
        url,
        data=payload,
        content_type="application/json",
        **(headers or {}),
    )


@pytest.mark.django_db
class TestCreateArticle:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory()
        channel = ChannelFactory(project=project, name="Updates")
        response = _post(
            client,
            f"/api/projects/{project.id}/articles",
            {"channel_id": str(channel.id)},
        )
        assert_that(response.status_code, equal_to(401))

    def test_non_contributor_returns_403(self, client, auth_headers) -> None:
        project = ProjectFactory()  # creator is a different user
        channel = ChannelFactory(project=project, name="Updates")
        response = _post(
            client,
            f"/api/projects/{project.id}/articles",
            {"channel_id": str(channel.id)},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(403))

    def test_unknown_project_returns_404(self, client, auth_headers) -> None:
        response = _post(
            client,
            "/api/projects/does-not-exist/articles",
            {"channel_id": "00000000-0000-0000-0000-000000000000"},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(404))

    def test_owner_can_create_draft(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        channel = ChannelFactory(project=project, name="Updates")

        response = _post(
            client,
            f"/api/projects/{project.id}/articles",
            {
                "channel_id": str(channel.id),
                "title": "First article",
                "body": "Body text",
            },
            auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        assert_that(
            response.json(),
            has_entries(
                title="First article",
                body="Body text",
                state="draft",
                channel=has_entries(id=str(channel.id), name="Updates"),
                project=has_entries(id=str(project.id)),
                author=has_entries(id=str(user.id)),
            ),
        )
        assert Article.objects.filter(project=project).count() == 1

    def test_channel_on_wrong_project_returns_404(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        other_project = ProjectFactory()
        foreign_channel = ChannelFactory(project=other_project, name="Updates")

        response = _post(
            client,
            f"/api/projects/{project.id}/articles",
            {"channel_id": str(foreign_channel.id)},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(404))

    def test_hero_image_on_wrong_project_returns_422(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        channel = ChannelFactory(project=project, name="Updates")
        foreign_image = ProjectImageFactory()  # belongs to a different project

        response = _post(
            client,
            f"/api/projects/{project.id}/articles",
            {
                "channel_id": str(channel.id),
                "hero_image_id": str(foreign_image.id),
            },
            auth_headers,
        )
        assert_that(response.status_code, equal_to(422))


@pytest.mark.django_db
class TestListArticles:
    def test_anonymous_sees_only_published(self, client) -> None:
        project = ProjectFactory()
        PublishedArticleFactory(project=project, title="Pub")
        ArticleFactory(project=project, title="Draft")

        response = client.get(f"/api/projects/{project.id}/articles")

        assert_that(response.status_code, equal_to(200))
        titles = [a["title"] for a in response.json()]
        assert_that(titles, equal_to(["Pub"]))

    def test_full_edit_user_sees_drafts_too(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        PublishedArticleFactory(project=project, title="Pub")
        ArticleFactory(project=project, title="Draft")

        response = client.get(f"/api/projects/{project.id}/articles", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_length(2))

    def test_unknown_project_returns_404(self, client) -> None:
        response = client.get("/api/projects/does-not-exist/articles")
        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestGetArticleById:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory()
        article = PublishedArticleFactory(project=project)
        response = client.get(f"/api/projects/{project.id}/articles/{article.id}")
        assert_that(response.status_code, equal_to(401))

    def test_published_visible_to_any_authed_user(self, client, auth_headers) -> None:
        project = ProjectFactory()
        article = PublishedArticleFactory(project=project)
        response = client.get(
            f"/api/projects/{project.id}/articles/{article.id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(id=str(article.id)))

    def test_draft_returns_403_for_non_author_non_full_edit(
        self, client, auth_headers
    ) -> None:
        project = ProjectFactory()  # creator is a different user
        draft = ArticleFactory(project=project)
        response = client.get(
            f"/api/projects/{project.id}/articles/{draft.id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(403))

    def test_draft_visible_to_author(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        draft = ArticleFactory(project=project, author=user)
        response = client.get(
            f"/api/projects/{project.id}/articles/{draft.id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(200))

    def test_article_on_different_project_returns_404(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        other_project = ProjectFactory()
        article = PublishedArticleFactory(project=other_project)

        response = client.get(
            f"/api/projects/{project.id}/articles/{article.id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(404))

    def test_unknown_article_returns_404(self, client, auth_headers) -> None:
        project = ProjectFactory()
        fake = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/projects/{project.id}/articles/{fake}", **auth_headers
        )
        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestGetArticleBySlug:
    def test_published_visible_to_anonymous(self, client) -> None:
        project = ProjectFactory(slug="my-proj")
        article = PublishedArticleFactory(project=project, title="X")
        article.slug = "x"
        article.save(update_fields=["slug"])

        response = client.get("/api/projects/my-proj/articles/by-slug/x")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(id=str(article.id)))

    def test_draft_404s_for_anonymous(self, client) -> None:
        project = ProjectFactory(slug="my-proj")
        draft = ArticleFactory(project=project)
        draft.slug = "draft-slug"
        draft.save(update_fields=["slug"])

        response = client.get("/api/projects/my-proj/articles/by-slug/draft-slug")
        assert_that(response.status_code, equal_to(404))

    def test_draft_visible_to_author(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user, slug="my-proj")
        draft = ArticleFactory(project=project, author=user)
        draft.slug = "draft-slug"
        draft.save(update_fields=["slug"])

        response = client.get(
            "/api/projects/my-proj/articles/by-slug/draft-slug",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(200))

    def test_unknown_slug_returns_404(self, client) -> None:
        ProjectFactory(slug="my-proj")
        response = client.get("/api/projects/my-proj/articles/by-slug/missing")
        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestPatchArticle:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory()
        article = ArticleFactory(project=project)
        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"title": "New"},
        )
        assert_that(response.status_code, equal_to(401))

    def test_non_full_edit_user_returns_403(self, client, auth_headers) -> None:
        project = ProjectFactory()  # creator is someone else
        article = ArticleFactory(project=project)
        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"title": "New"},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(403))

    def test_owner_can_update_title(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"title": "Updated"},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        article.refresh_from_db()
        assert_that(article.title, equal_to("Updated"))

    def test_article_on_different_project_returns_404(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        other = ProjectFactory()
        article = ArticleFactory(project=other)

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"title": "Updated"},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestPublishArticle:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory()
        article = ArticleFactory(project=project)
        response = _post(
            client,
            f"/api/projects/{project.id}/articles/{article.id}/publish",
            {},
        )
        assert_that(response.status_code, equal_to(401))

    def test_non_full_edit_user_returns_403(self, client, auth_headers) -> None:
        project = ProjectFactory()
        article = ArticleFactory(project=project)
        response = _post(
            client,
            f"/api/projects/{project.id}/articles/{article.id}/publish",
            {},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(403))

    def test_owner_can_publish(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)

        response = _post(
            client,
            f"/api/projects/{project.id}/articles/{article.id}/publish",
            {},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        article.refresh_from_db()
        assert_that(article.state, equal_to(ArticleState.PUBLISHED))
        assert article.slug  # slug assigned on publish

    def test_publish_without_body_returns_422(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project, body="")

        response = _post(
            client,
            f"/api/projects/{project.id}/articles/{article.id}/publish",
            {},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(422))

    def test_unknown_article_returns_404(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        fake = "00000000-0000-0000-0000-000000000000"
        response = _post(
            client,
            f"/api/projects/{project.id}/articles/{fake}/publish",
            {},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestDeleteArticle:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory()
        article = ArticleFactory(project=project)
        response = client.delete(f"/api/projects/{project.id}/articles/{article.id}")
        assert_that(response.status_code, equal_to(401))

    def test_non_full_edit_user_returns_403(self, client, auth_headers) -> None:
        project = ProjectFactory()
        article = ArticleFactory(project=project)
        response = client.delete(
            f"/api/projects/{project.id}/articles/{article.id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(403))

    def test_owner_can_delete(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)

        response = client.delete(
            f"/api/projects/{project.id}/articles/{article.id}",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(204))
        assert not Article.objects.filter(pk=article.id).exists()

    def test_article_on_different_project_returns_404(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        other = ProjectFactory()
        article = ArticleFactory(project=other)

        response = client.delete(
            f"/api/projects/{project.id}/articles/{article.id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestRouterHasNoOrmAccess:
    """Spec invariant — `api/routers/articles.py` SHALL NOT reference
    `Article.objects`, `Channel.objects`, or `FollowChannelPreference.objects`
    directly. All DB access goes through HANDLERS / REPO.
    """

    def test_no_orm_imports(self) -> None:
        src = Path(__file__).resolve().parent.parent / "routers" / "articles.py"
        text = src.read_text()
        for forbidden in (
            "Article.objects",
            "Channel.objects",
            "FollowChannelPreference.objects",
        ):
            assert forbidden not in text, (
                f"{forbidden} must not appear in api/routers/articles.py"
            )
