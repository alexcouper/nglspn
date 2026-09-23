import uuid

from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
    has_key,
    is_,
    none,
    not_,
)

from apps.articles.models import ArticleGlobalVisibility
from apps.projects.models import ContributorRole, ProjectContributor, ProjectStatus
from tests.factories import (
    ArticleFactory,
    PendingArticleFactory,
    ProjectCategoryFactory,
    ProjectFactory,
    ProjectImageFactory,
    PublishedArticleFactory,
    UserFactory,
    give_avatar,
)


def approved_project(**kwargs):
    return ProjectFactory(status=ProjectStatus.APPROVED, **kwargs)


def make_tipster(user, project) -> ProjectContributor:
    return ProjectContributor.objects.create(
        project=project, user=user, role=ContributorRole.TIPSTER, full_edit=True
    )


def listed_ids(response) -> list[str]:
    return [item["id"] for item in response.json()]


class TestExternalPromotionPreference:
    def test_new_user_has_external_promotions_opted_in_by_default(self, db) -> None:
        user = UserFactory()

        assert_that(user.opt_in_to_external_promotions, equal_to(True))

    def test_update_external_promotion_preference_via_api(
        self, client, user, auth_headers
    ) -> None:
        response = client.put(
            "/api/auth/me",
            data={"opt_in_to_external_promotions": False},
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        user.refresh_from_db()
        assert_that(user.opt_in_to_external_promotions, equal_to(False))

    def test_get_me_returns_external_promotion_preference(
        self, client, user, auth_headers
    ) -> None:
        response = client.get("/api/auth/me", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(opt_in_to_external_promotions=True),
        )


class TestPublicProfile:
    def test_get_public_profile_returns_only_public_fields(self, client, user) -> None:
        user.first_name = "John"
        user.last_name = "Doe"
        user.info = "A passionate developer"
        user.save()

        response = client.get(f"/api/users/{user.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                id=str(user.id),
                first_name="John",
                last_name="Doe",
                info="A passionate developer",
            ),
        )
        # This check ensures no extra fields are returned
        assert_that(
            list(response.json().keys()),
            contains_inanyorder(
                "id",
                "first_name",
                "last_name",
                "info",
                "is_system_user",
                "avatar_url",
                "created_at",
            ),
        )

    def test_get_public_profile_does_not_leak_private_settings(
        self, client, user
    ) -> None:
        response = client.get(f"/api/users/{user.id}")

        data = response.json()
        assert_that(data, not_(has_key("email")))
        assert_that(data, not_(has_key("opt_in_to_external_promotions")))
        assert_that(data, not_(has_key("article_trust")))

    def test_get_public_profile_nonexistent_user_returns_404(self, client, db) -> None:
        fake_id = uuid.uuid4()
        response = client.get(f"/api/users/{fake_id}")

        assert_that(response.status_code, equal_to(404))
        assert_that(response.json(), has_entries(detail="User not found"))

    def test_get_public_profile_with_empty_info(self, client, db) -> None:
        user = UserFactory(first_name="Jane", last_name="Smith", info="")

        response = client.get(f"/api/users/{user.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                first_name="Jane",
                last_name="Smith",
                info="",
            ),
        )


class TestPublicProfileVisibility:
    def test_inactive_account_has_no_profile(self, client, db) -> None:
        user = UserFactory(is_active=False)

        response = client.get(f"/api/users/{user.id}")

        assert_that(response.status_code, equal_to(404))

    def test_system_user_has_no_profile(self, client, db) -> None:
        user = UserFactory(is_system_user=True)

        response = client.get(f"/api/users/{user.id}")

        assert_that(response.status_code, equal_to(404))

    def test_profile_carries_the_avatar_url(self, client, user) -> None:
        avatar = give_avatar(user)

        response = client.get(f"/api/users/{user.id}")

        assert_that(response.json()["avatar_url"], equal_to(f"{avatar.url}"))

    def test_profile_without_avatar_has_null_url(self, client, user) -> None:
        response = client.get(f"/api/users/{user.id}")

        assert_that(response.json()["avatar_url"], is_(none()))


class TestPublicProjects:
    def test_owned_come_before_tipped_off_with_their_role(self, client, user) -> None:
        owned = approved_project(creator=user)
        tipped = approved_project()
        make_tipster(user, tipped)

        response = client.get(f"/api/users/{user.id}/projects")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            [(item["id"], item["role"]) for item in response.json()],
            contains_exactly((str(owned.id), "owner"), (str(tipped.id), "tipster")),
        )

    def test_unapproved_projects_are_absent_even_for_the_owner(
        self, client, user, auth_headers
    ) -> None:
        for status in (
            ProjectStatus.DRAFT,
            ProjectStatus.PENDING,
            ProjectStatus.REJECTED,
            ProjectStatus.ICE_BOX,
        ):
            ProjectFactory(creator=user, status=status)

        response = client.get(f"/api/users/{user.id}/projects", **auth_headers)

        assert_that(response.json(), empty())

    def test_item_carries_category_and_tagline(self, client, user) -> None:
        category = ProjectCategoryFactory(name="Environment")
        project = approved_project(creator=user, category=category, tagline="Plots")

        response = client.get(f"/api/users/{user.id}/projects")

        assert_that(
            response.json()[0],
            has_entries(
                slug=project.slug,
                title=project.title,
                tagline="Plots",
                category_name="Environment",
            ),
        )

    def test_thumbnail_follows_the_main_image(self, client, user) -> None:
        project = approved_project(creator=user)
        image = ProjectImageFactory(project=project, is_main=True)

        response = client.get(f"/api/users/{user.id}/projects")

        assert_that(response.json()[0]["main_image_thumb_url"], equal_to(image.url))

    def test_no_image_means_null_thumbnail(self, client, user) -> None:
        approved_project(creator=user)

        response = client.get(f"/api/users/{user.id}/projects")

        assert_that(response.json()[0]["main_image_thumb_url"], is_(none()))

    def test_no_profile_no_list(self, client, db) -> None:
        system = UserFactory(is_system_user=True)

        assert_that(
            client.get(f"/api/users/{system.id}/projects").status_code, equal_to(404)
        )
        assert_that(
            client.get(f"/api/users/{uuid.uuid4()}/projects").status_code,
            equal_to(404),
        )


class TestPublicArticles:
    def test_visible_articles_newest_first_with_their_project(
        self, client, user
    ) -> None:
        project = approved_project(creator=user)
        older = PublishedArticleFactory(
            project=project,
            author=user,
            title="Older",
            published_at="2026-01-01T00:00Z",
        )
        newer = PublishedArticleFactory(
            project=project,
            author=user,
            title="Newer",
            published_at="2026-03-01T00:00Z",
        )

        response = client.get(f"/api/users/{user.id}/articles")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            listed_ids(response), contains_exactly(str(newer.id), str(older.id))
        )
        assert_that(
            response.json()[0]["project"],
            has_entries(slug=project.slug, title=project.title),
        )

    def test_hidden_articles_are_absent_even_for_the_author(
        self, client, user, auth_headers
    ) -> None:
        project = approved_project(creator=user)
        ArticleFactory(project=project, author=user)
        PendingArticleFactory(project=project, author=user)
        PublishedArticleFactory(
            project=project,
            author=user,
            global_visibility=ArticleGlobalVisibility.DEMOTED,
        )

        response = client.get(f"/api/users/{user.id}/articles", **auth_headers)

        assert_that(response.json(), empty())

    def test_articles_on_unapproved_projects_are_absent(self, client, user) -> None:
        iced = ProjectFactory(creator=user, status=ProjectStatus.ICE_BOX)
        PublishedArticleFactory(project=iced, author=user)

        response = client.get(f"/api/users/{user.id}/articles")

        assert_that(response.json(), empty())

    def test_someone_elses_article_is_not_listed(self, client, user) -> None:
        project = approved_project(creator=user)
        PublishedArticleFactory(project=project, author=UserFactory())

        response = client.get(f"/api/users/{user.id}/articles")

        assert_that(response.json(), empty())

    def test_no_profile_no_list(self, client, db) -> None:
        inactive = UserFactory(is_active=False)

        assert_that(
            client.get(f"/api/users/{inactive.id}/articles").status_code,
            equal_to(404),
        )
