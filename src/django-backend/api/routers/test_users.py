import uuid

import pytest
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

from api.auth.jwt import create_access_token
from apps.articles.models import ArticleGlobalVisibility
from apps.follows.models import Follow, FollowedChannel
from apps.projects.models import ContributorRole, ProjectContributor, ProjectStatus
from tests.factories import (
    ArticleFactory,
    AuthorArticleFactory,
    ImageFactory,
    PendingArticleFactory,
    ProjectCategoryFactory,
    ProjectFactory,
    PublishedArticleFactory,
    PublishedAuthorArticleFactory,
    UserFactory,
    give_avatar,
    personal_channel,
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
                "is_followed",
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
        image = ImageFactory(project=project, is_main=True)

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


def follow(client, user_id, headers):
    return client.post(f"/api/users/{user_id}/follow", **headers)


def unfollow(client, user_id, headers):
    return client.delete(f"/api/users/{user_id}/follow", **headers)


def is_followed(client, user_id, headers) -> bool:
    return client.get(f"/api/users/{user_id}", **headers).json()["is_followed"]


@pytest.mark.django_db
class TestFollowAPerson:
    def test_anonymous_is_401_on_both(self, client, user) -> None:
        assert_that(follow(client, user.id, {}).status_code, equal_to(401))
        assert_that(unfollow(client, user.id, {}).status_code, equal_to(401))

    def test_follow_then_profile_reports_it(self, client, auth_headers) -> None:
        person = UserFactory()

        response = follow(client, person.id, auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(is_followed=True))
        assert_that(is_followed(client, person.id, auth_headers), equal_to(True))

    def test_anonymous_profile_reports_not_followed(self, client, user, auth_headers):
        person = UserFactory()
        follow(client, person.id, auth_headers)

        assert_that(
            client.get(f"/api/users/{person.id}").json()["is_followed"], equal_to(False)
        )

    def test_follow_is_idempotent(self, client, auth_headers) -> None:
        person = UserFactory()
        follow(client, person.id, auth_headers)

        assert_that(follow(client, person.id, auth_headers).status_code, equal_to(200))
        assert_that(Follow.objects.filter(followed_user=person).count(), equal_to(1))

    def test_following_someone_who_published_enrols_their_channel(
        self, client, user, auth_headers
    ) -> None:
        person = UserFactory()
        channel = personal_channel(person)

        follow(client, person.id, auth_headers)

        assert_that(
            FollowedChannel.objects.filter(follow__user=user, channel=channel).exists(),
            equal_to(True),
        )

    def test_unfollow_is_204_and_clears_rows(self, client, user, auth_headers) -> None:
        person = UserFactory()
        personal_channel(person)
        follow(client, person.id, auth_headers)

        response = unfollow(client, person.id, auth_headers)

        assert_that(response.status_code, equal_to(204))
        assert_that(Follow.objects.filter(user=user).exists(), equal_to(False))
        assert_that(is_followed(client, person.id, auth_headers), equal_to(False))

    def test_unfollow_when_not_following_is_204(self, client, auth_headers) -> None:
        assert_that(
            unfollow(client, UserFactory().id, auth_headers).status_code, equal_to(204)
        )

    def test_self_follow_is_400(self, client, user, auth_headers) -> None:
        response = follow(client, user.id, auth_headers)

        assert_that(response.status_code, equal_to(400))
        assert_that(Follow.objects.filter(user=user).exists(), equal_to(False))

    def test_system_and_inactive_users_are_404(self, client, auth_headers) -> None:
        for person in (UserFactory(is_system_user=True), UserFactory(is_active=False)):
            assert_that(
                follow(client, person.id, auth_headers).status_code, equal_to(404)
            )
            assert_that(
                unfollow(client, person.id, auth_headers).status_code, equal_to(404)
            )


@pytest.mark.django_db
class TestPublicArticlesMixBothKinds:
    def test_author_owned_article_is_listed_with_a_null_project(self, client, user):
        project = approved_project(creator=user)
        on_project = PublishedArticleFactory(project=project, author=user)
        owned = PublishedAuthorArticleFactory(author=user)

        response = client.get(f"/api/users/{user.id}/articles")

        by_id = {row["id"]: row for row in response.json()}
        assert_that(set(by_id), equal_to({str(on_project.id), str(owned.id)}))
        assert_that(by_id[str(owned.id)]["project"], equal_to(None))
        assert_that(
            by_id[str(on_project.id)]["project"], has_entries(slug=project.slug)
        )

    def test_a_visitor_sees_no_draft_or_pending_author_owned_article(
        self, client, user
    ):
        AuthorArticleFactory(author=user)
        PublishedAuthorArticleFactory(
            author=user, global_visibility=ArticleGlobalVisibility.PENDING
        )

        assert_that(client.get(f"/api/users/{user.id}/articles").json(), empty())


@pytest.mark.django_db
class TestAuthorArticleBySlug:
    def url(self, article) -> str:
        return f"/api/users/{article.author_id}/articles/by-slug/{article.slug}"

    def test_published_renders_for_anyone(self, client, user) -> None:
        article = PublishedAuthorArticleFactory(author=user, slug="hello")

        response = client.get(self.url(article))

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(slug="hello", project=None))
        assert_that(response.json()["author"], has_entries(id=str(user.id)))

    def test_draft_404s_for_the_public_and_renders_for_the_author(
        self, client, user, auth_headers
    ) -> None:
        draft = AuthorArticleFactory(author=user, slug="draft")

        assert_that(client.get(self.url(draft)).status_code, equal_to(404))
        assert_that(
            client.get(self.url(draft), **auth_headers).status_code, equal_to(200)
        )

    def test_pending_and_demoted_render_at_their_own_url(self, client, user) -> None:
        for visibility in (
            ArticleGlobalVisibility.PENDING,
            ArticleGlobalVisibility.DEMOTED,
        ):
            article = PublishedAuthorArticleFactory(
                author=user, global_visibility=visibility, slug=str(visibility)
            )

            assert_that(client.get(self.url(article)).status_code, equal_to(404))
            # The author sees their own.
            own_headers = {
                "HTTP_AUTHORIZATION": f"Bearer {create_access_token(user.id)}"
            }
            assert_that(
                client.get(self.url(article), **own_headers).status_code, equal_to(200)
            )

    def test_wrong_author_in_the_url_is_404(self, client, user) -> None:
        PublishedAuthorArticleFactory(author=user, slug="hello")

        response = client.get(f"/api/users/{UserFactory().id}/articles/by-slug/hello")

        assert_that(response.status_code, equal_to(404))

    def test_a_project_articles_slug_is_not_served_here(self, client, user) -> None:
        project = approved_project(creator=user)
        article = PublishedArticleFactory(project=project, author=user, slug="hello")

        assert_that(client.get(self.url(article)).status_code, equal_to(404))

    def test_an_author_owned_article_is_not_served_under_a_project(self, client, user):
        project = approved_project(creator=user)
        PublishedAuthorArticleFactory(author=user, slug="hello")

        response = client.get(f"/api/projects/{project.slug}/articles/by-slug/hello")

        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestFollowedPersonsChannelToggle:
    def url(self, person, channel) -> str:
        return f"/api/users/{person.id}/follow/channels/{channel.id}"

    def test_unticking_the_one_channel_unfollows_the_person(
        self, client, user, auth_headers
    ) -> None:
        person = UserFactory()
        channel = personal_channel(person)
        follow(client, person.id, auth_headers)

        response = client.delete(self.url(person, channel), **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(is_followed=False))
        assert_that(Follow.objects.filter(user=user).exists(), equal_to(False))

    def test_ticking_it_back_on_needs_the_follow(self, client, auth_headers) -> None:
        person = UserFactory()
        channel = personal_channel(person)

        response = client.post(self.url(person, channel), **auth_headers)

        assert_that(response.status_code, equal_to(404))

    def test_ticking_it_on_under_a_follow(self, client, user, auth_headers) -> None:
        person = UserFactory()
        follow(client, person.id, auth_headers)
        channel = personal_channel(person)
        FollowedChannel.objects.filter(follow__user=user).delete()

        response = client.post(self.url(person, channel), **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(), has_entries(channel_name="Articles", followed=True)
        )

    def test_someone_elses_channel_is_404(self, client, auth_headers) -> None:
        person, other = UserFactory(), UserFactory()
        follow(client, person.id, auth_headers)

        response = client.post(
            self.url(person, personal_channel(other)), **auth_headers
        )

        assert_that(response.status_code, equal_to(404))
