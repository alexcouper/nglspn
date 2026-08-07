from pathlib import Path

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_entries,
    has_length,
)

from apps.articles.models import Article, ArticleState
from apps.projects.models import (
    ImageVariant,
    ProjectStatus,
    VariantSize,
)
from tests.factories import (
    ArticleFactory,
    ChannelFactory,
    ProjectFactory,
    ProjectImageFactory,
    PublishedArticleFactory,
    article_image,
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

    def test_listing_image_on_wrong_project_returns_422(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        foreign_image = ProjectImageFactory()  # belongs to a different project

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"listing_image_id": str(foreign_image.id)},
            auth_headers,
        )
        assert_that(response.status_code, equal_to(422))


@pytest.mark.django_db
class TestListArticles:
    def test_anonymous_sees_only_published(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
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

    def test_pending_project_404s_for_anonymous(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.PENDING)
        PublishedArticleFactory(project=project, title="Pub")

        response = client.get(f"/api/projects/{project.id}/articles")

        assert_that(response.status_code, equal_to(404))

    def test_pending_project_404s_for_non_editor(self, client, auth_headers) -> None:
        project = ProjectFactory(status=ProjectStatus.PENDING)
        PublishedArticleFactory(project=project, title="Pub")

        response = client.get(f"/api/projects/{project.id}/articles", **auth_headers)

        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestGetArticleById:
    def test_unauthenticated_returns_401(self, client) -> None:
        project = ProjectFactory()
        article = PublishedArticleFactory(project=project)
        response = client.get(f"/api/projects/{project.id}/articles/{article.id}")
        assert_that(response.status_code, equal_to(401))

    def test_published_visible_to_any_authed_user(self, client, auth_headers) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
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
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        draft = ArticleFactory(project=project)
        response = client.get(
            f"/api/projects/{project.id}/articles/{draft.id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(403))

    def test_pending_project_404s_for_authed_non_editor(
        self, client, auth_headers
    ) -> None:
        project = ProjectFactory(status=ProjectStatus.PENDING)
        article = PublishedArticleFactory(project=project)
        response = client.get(
            f"/api/projects/{project.id}/articles/{article.id}",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(404))

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
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        fake = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/projects/{project.id}/articles/{fake}", **auth_headers
        )
        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestGetArticleBySlug:
    def test_published_visible_to_anonymous(self, client) -> None:
        project = ProjectFactory(slug="my-proj", status=ProjectStatus.APPROVED)
        article = PublishedArticleFactory(project=project, title="X")
        article.slug = "x"
        article.save(update_fields=["slug"])

        response = client.get("/api/projects/my-proj/articles/by-slug/x")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(id=str(article.id)))

    def test_draft_404s_for_anonymous(self, client) -> None:
        project = ProjectFactory(slug="my-proj", status=ProjectStatus.APPROVED)
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
        ProjectFactory(slug="my-proj", status=ProjectStatus.APPROVED)
        response = client.get("/api/projects/my-proj/articles/by-slug/missing")
        assert_that(response.status_code, equal_to(404))

    def test_pending_project_404s_for_anonymous(self, client) -> None:
        project = ProjectFactory(slug="my-proj", status=ProjectStatus.PENDING)
        article = PublishedArticleFactory(project=project, title="X")
        article.slug = "x"
        article.save(update_fields=["slug"])

        response = client.get("/api/projects/my-proj/articles/by-slug/x")

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

    def test_owner_can_set_and_clear_summary(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project, body="The body opening line.")

        set_response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"summary": "An authored hook."},
            auth_headers,
        )
        assert_that(set_response.status_code, equal_to(200))
        assert_that(set_response.json()["summary"], equal_to("An authored hook."))
        assert_that(
            set_response.json()["summary_display"], equal_to("An authored hook.")
        )

        clear_response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"summary": ""},
            auth_headers,
        )
        assert_that(clear_response.status_code, equal_to(200))
        assert_that(clear_response.json()["summary"], equal_to(""))
        assert_that(
            clear_response.json()["summary_display"],
            equal_to("The body opening line."),
        )

    def test_patch_without_the_image_key_keeps_the_image(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        chosen = _sized_image(article)
        _choose(client, project, article, auth_headers, chosen)

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"title": "Updated"},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        article.refresh_from_db()
        assert_that(article.listing_image_id, equal_to(chosen.id))

    def test_explicit_null_clears_the_image_on_a_draft(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        _choose(client, project, article, auth_headers, _sized_image(article))

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"listing_image_id": None, "listing_image_mode": "none"},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["listing_image_id"], equal_to(None))
        article.refresh_from_db()
        assert_that(article.listing_image_id, equal_to(None))

    def test_explicit_null_on_a_published_article_is_accepted(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = PublishedArticleFactory(project=project, slug="a-post")
        _choose(client, project, article, auth_headers, _sized_image(article))

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"listing_image_id": None, "listing_image_mode": "none"},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["listing_image_id"], equal_to(None))


SOURCE_WIDTH = 4000
SOURCE_HEIGHT = 2000
CARD_RATIO = 16 / 9


def _sized_image(article, width=SOURCE_WIDTH, height=SOURCE_HEIGHT):
    """An image uploaded for `article`, with dimensions so crops can validate."""
    return article_image(article, width=width, height=height)


def _crop(x: float, y: float, w: float) -> dict[str, float]:
    """A 16:9 crop of the source above, with a consistent stored ratio."""
    h = (w * SOURCE_WIDTH) / (CARD_RATIO * SOURCE_HEIGHT)
    return {"x": x, "y": y, "w": w, "h": h, "ratio": CARD_RATIO}


LISTING_CROP = _crop(x=0.2, y=0.3, w=0.6)


def _choose(client, project, article, auth_headers, image, crop=None):
    """Set the article's listing image through the API, as the wizard does."""
    payload = {"listing_image_id": str(image.id), "listing_image_mode": "chosen"}
    if crop is not None:
        payload["listing_crop"] = crop
    response = _patch(
        client,
        f"/api/projects/{project.id}/articles/{article.id}",
        payload,
        auth_headers,
    )
    assert_that(response.status_code, equal_to(200))
    return response


@pytest.mark.django_db
class TestListingImageMode:
    def test_a_new_article_starts_in_auto(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        channel = ChannelFactory(project=project, name="Updates")

        response = _post(
            client,
            f"/api/projects/{project.id}/articles",
            {"channel_id": str(channel.id), "title": "Fresh"},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        assert_that(response.json()["listing_image_mode"], equal_to("auto"))
        assert_that(response.json()["listing_image_id"], equal_to(None))

    def test_auto_adopts_the_first_upload_on_save(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        first = _sized_image(article)
        _sized_image(article)

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"title": "Saved"},
            auth_headers,
        )

        assert_that(
            response.json(),
            has_entries(
                listing_image_id=str(first.id),
                listing_image_mode="auto",
                listing_crop=None,
            ),
        )

    def test_choosing_an_image_and_a_crop_round_trips(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        _sized_image(article)
        chosen = _sized_image(article)

        response = _choose(
            client, project, article, auth_headers, chosen, crop=LISTING_CROP
        )

        assert_that(
            response.json(),
            has_entries(
                listing_image_id=str(chosen.id),
                listing_image_mode="chosen",
            ),
        )
        assert_that(response.json()["listing_crop"], has_entries(x=0.2, w=0.6))
        article.refresh_from_db()
        assert_that(article.listing_crop, has_entries(x=0.2, w=0.6))

    def test_a_chosen_image_survives_a_later_save(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        _sized_image(article)
        chosen = _sized_image(article)
        _choose(client, project, article, auth_headers, chosen)

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"title": "Saved again"},
            auth_headers,
        )

        assert_that(response.json()["listing_image_id"], equal_to(str(chosen.id)))

    def test_removal_is_not_undone_by_a_later_save(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        _sized_image(article)
        _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"listing_image_id": None, "listing_image_mode": "none"},
            auth_headers,
        )

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"title": "Saved again"},
            auth_headers,
        )

        assert_that(
            response.json(),
            has_entries(listing_image_id=None, listing_image_mode="none"),
        )

    def test_an_unknown_mode_is_rejected(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"listing_image_mode": "nonsense"},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(422))
        article.refresh_from_db()
        assert_that(article.listing_image_mode, equal_to("auto"))


@pytest.mark.django_db
class TestArticleCrops:
    def test_explicit_null_clears_the_crop(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        chosen = _sized_image(article)
        _choose(client, project, article, auth_headers, chosen, crop=LISTING_CROP)

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"listing_crop": None},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["listing_crop"], equal_to(None))
        article.refresh_from_db()
        assert_that(article.listing_crop, equal_to(None))

    def test_replacing_the_image_drops_a_stale_crop(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        chosen = _sized_image(article)
        replacement = _sized_image(article)
        _choose(client, project, article, auth_headers, chosen, crop=LISTING_CROP)

        _choose(client, project, article, auth_headers, replacement)

        article.refresh_from_db()
        assert_that(article.listing_image_id, equal_to(replacement.id))
        assert_that(article.listing_crop, equal_to(None))

    def test_a_crop_overhanging_the_image_is_accepted(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        chosen = _sized_image(article)

        _choose(
            client,
            project,
            article,
            auth_headers,
            chosen,
            crop=_crop(x=-0.25, y=0.1, w=1.5),
        )

        article.refresh_from_db()
        assert_that(article.listing_crop, has_entries(x=-0.25, w=1.5))

    def test_a_crop_that_misses_the_image_entirely_returns_422(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        chosen = _sized_image(article)
        _choose(client, project, article, auth_headers, chosen)

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"listing_crop": _crop(x=1.4, y=0.3, w=0.6)},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(422))
        article.refresh_from_db()
        assert_that(article.listing_crop, equal_to(None))

    def test_a_crop_at_the_wrong_ratio_returns_422(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        chosen = _sized_image(article)
        _choose(client, project, article, auth_headers, chosen)
        four_by_three = {"x": 0.1, "y": 0.2, "w": 0.6, "h": 0.9, "ratio": 4 / 3}

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"listing_crop": four_by_three},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(422))
        article.refresh_from_db()
        assert_that(article.listing_crop, equal_to(None))

    def test_a_crop_with_no_listing_image_returns_422(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)

        response = _patch(
            client,
            f"/api/projects/{project.id}/articles/{article.id}",
            {"listing_crop": LISTING_CROP},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(422))


@pytest.mark.django_db
class TestArticleListCardCrop:
    def test_list_carries_the_stored_crop(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.APPROVED)
        article = PublishedArticleFactory(project=project, slug="a-post")
        chosen = _sized_image(article)
        _choose(client, project, article, auth_headers, chosen, crop=LISTING_CROP)

        response = client.get(f"/api/projects/{project.id}/articles")

        assert_that(response.json()[0]["listing_crop"], has_entries(x=0.2, w=0.6))
        assert_that(
            response.json()[0]["listing_image_url"], contains_string(chosen.storage_key)
        )

    def test_list_crop_is_null_without_one(self, client, user, auth_headers) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.APPROVED)
        article = PublishedArticleFactory(project=project, slug="b-post")
        _choose(client, project, article, auth_headers, _sized_image(article))

        response = client.get(f"/api/projects/{project.id}/articles")

        assert_that(response.json()[0]["listing_crop"], equal_to(None))

    def test_list_image_is_null_for_an_imageless_article(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        PublishedArticleFactory(project=project, slug="c-post")

        response = client.get(f"/api/projects/{project.id}/articles")

        assert_that(
            response.json()[0],
            has_entries(listing_image_url=None, listing_crop=None),
        )


@pytest.mark.django_db
class TestArticleListSummary:
    def test_list_falls_back_to_derived_summary(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        PublishedArticleFactory(
            project=project,
            slug="a-post",
            body="# Heading\n\nDerived from the body.",
            summary="",
        )

        response = client.get(f"/api/projects/{project.id}/articles")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()[0]["summary"], equal_to("Derived from the body."))

    def test_list_prefers_the_authored_summary(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)
        PublishedArticleFactory(
            project=project,
            slug="b-post",
            body="Derived from the body.",
            summary="Authored.",
        )

        response = client.get(f"/api/projects/{project.id}/articles")

        assert_that(response.json()[0]["summary"], equal_to("Authored."))


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

    def test_publish_without_an_image_succeeds(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)

        response = _post(
            client,
            f"/api/projects/{project.id}/articles/{article.id}/publish",
            {},
            auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["listing_image_id"], equal_to(None))

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


class TestRouterHasNoOrmAccess:
    """Spec invariant — `api/routers/articles.py` SHALL NOT reach the database
    directly. All DB access goes through HANDLERS / REPO.

    Two spellings, because banning `<Model>.objects` alone misses the one the
    file actually used: `get_object_or_404(ProjectImage, ...)` takes the model
    class and reaches `_default_manager` itself, writing no `.objects` at all.
    Model names are not banned — they are legitimate return annotations.

    It is a substring scan, so an alias or `_default_manager` defeats it. It
    raises the cost of the mistake; it does not make it impossible.
    """

    def test_no_direct_orm_access(self) -> None:
        src = Path(__file__).resolve().parent.parent / "routers" / "articles.py"
        text = src.read_text()
        for forbidden in (
            "Article.objects",
            "Channel.objects",
            "FollowedChannel.objects",
            "ProjectImage.objects",
            "get_object_or_404",
        ):
            assert forbidden not in text, (
                f"{forbidden} must not appear in api/routers/articles.py"
            )


@pytest.mark.django_db
class TestArticleListingImage:
    """The editor resolves an article's listing image from the article
    response. It cannot use `ProjectResponse.images`, which excludes article
    uploads."""

    def test_article_response_carries_the_full_listing_image(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        image = _sized_image(article)
        ImageVariant.objects.create(
            image=image,
            size=VariantSize.LARGE,
            storage_key="variants/large.jpg",
            width=1536,
            height=864,
            file_size=2048,
        )
        _choose(client, project, article, auth_headers, image)

        response = client.get(
            f"/api/projects/{project.id}/articles/{article.id}", **auth_headers
        )

        assert_that(response.status_code, equal_to(200))
        payload = response.json()["listing_image"]
        assert_that(payload, has_entries(id=str(image.id)))
        assert_that(payload["variants"], has_length(1))
        assert_that(payload["variants"][0], has_entries(size="large"))

    def test_listing_image_is_null_when_the_article_has_none(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)

        response = client.get(
            f"/api/projects/{project.id}/articles/{article.id}", **auth_headers
        )

        assert_that(response.json()["listing_image"], equal_to(None))

    def test_the_listing_image_stays_out_of_the_project_gallery(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.APPROVED)
        article = ArticleFactory(project=project)
        _choose(client, project, article, auth_headers, _sized_image(article))

        response = client.get(f"/api/projects/{project.id}")

        assert_that(response.json()["images"], has_length(0))


@pytest.mark.django_db
class TestArticleImageList:
    """`ArticleOut.images` is the listing-image wizard's selection list."""

    def test_carries_the_articles_own_uploads_in_upload_order(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        first = article_image(article)
        second = article_image(article)

        response = client.get(
            f"/api/projects/{project.id}/articles/{article.id}", **auth_headers
        )

        ids = [image["id"] for image in response.json()["images"]]
        assert_that(ids, equal_to([str(first.id), str(second.id)]))

    def test_excludes_project_images_and_other_articles_uploads(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(owner=user)
        article = ArticleFactory(project=project)
        mine = article_image(article)
        ProjectImageFactory(project=project)
        article_image(ArticleFactory(project=project))

        response = client.get(
            f"/api/projects/{project.id}/articles/{article.id}", **auth_headers
        )

        ids = [image["id"] for image in response.json()["images"]]
        assert_that(ids, equal_to([str(mine.id)]))
