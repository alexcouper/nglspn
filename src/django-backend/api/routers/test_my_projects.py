import json
from unittest.mock import patch

from hamcrest import (
    assert_that,
    contains_inanyorder,
    equal_to,
    has_entries,
    has_key,
    has_length,
    is_,
    none,
)

from apps.projects.models import (
    ContributorRole,
    Project,
    ProjectContributor,
    ProjectStatus,
)
from apps.users.seed import get_community_user
from tests.factories import ProjectFactory, ProjectImageFactory


def _ready_draft(**kwargs):
    project = ProjectFactory(
        status=ProjectStatus.DRAFT,
        title=kwargs.pop("title", "Ready Draft"),
        description=kwargs.pop("description", "A description"),
        submission_month="",
        slug=None,
        published_at=None,
        **kwargs,
    )
    ProjectImageFactory(project=project, is_main=True, upload_status="uploaded")
    return project


class TestListMyProjects:
    def test_list_my_projects_returns_owned_projects(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        ProjectFactory.create_batch(3, owner=user)
        ProjectFactory()  # Another user's project

        response = client.get("/api/my/projects", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_length(3))


class TestListMySuggestions:
    def test_empty_when_no_suggestions(self, client, user, auth_headers) -> None:
        ProjectFactory(owner=user)  # self-owned

        response = client.get("/api/my/projects/suggestions", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_length(0))

    def test_returns_community_suggested_projects(
        self, client, user, auth_headers
    ) -> None:
        # A community-suggested project: seed user is OWNER, calling user is SUGGESTER.
        seed = get_community_user()
        project = ProjectFactory(creator=user, _contributor=False)
        ProjectContributor.objects.create(
            project=project, user=seed, role=ContributorRole.OWNER, full_edit=True
        )
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.SUGGESTER,
            full_edit=True,
        )

        response = client.get("/api/my/projects/suggestions", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_length(1))
        assert_that(
            response.json()[0],
            has_entries(id=str(project.id)),
        )

    def test_excludes_suggester_with_full_edit_disabled(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()  # owned by someone else
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.SUGGESTER,
            full_edit=False,
        )

        response = client.get("/api/my/projects/suggestions", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_length(0))

    def test_requires_authentication(self, client, db) -> None:
        response = client.get("/api/my/projects/suggestions")

        assert_that(response.status_code, equal_to(401))


class TestCommunityOwnedCreate:
    def test_community_owned_flag_creates_seed_owner_and_suggester(
        self, client, user, auth_headers
    ) -> None:
        payload = {
            "website_url": "https://made-by-someone-else.com",
            "description": "A cool community-suggested project",
            "community_owned": True,
        }

        response = client.post(
            "/api/my/projects",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        body = response.json()
        seed = get_community_user()
        roles = {c["user"]["id"]: c["role"] for c in body["contributors"]}
        assert_that(roles[str(seed.id)], equal_to("owner"))
        assert_that(roles[str(user.id)], equal_to("suggester"))
        assert_that(body["creator"]["id"], equal_to(str(user.id)))

    def test_default_omitted_creates_self_owned(
        self, client, user, auth_headers
    ) -> None:
        payload = {
            "website_url": "https://my-own-project.com",
            "description": "Self-owned",
        }

        response = client.post(
            "/api/my/projects",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        body = response.json()
        assert_that(body["contributors"], has_length(1))
        assert_that(body["contributors"][0]["role"], equal_to("owner"))
        assert_that(body["contributors"][0]["user"]["id"], equal_to(str(user.id)))


class TestCreateProject:
    def test_create_project_with_url(self, client, user, auth_headers) -> None:
        payload = {"website_url": "https://example.com", "description": "My project"}

        response = client.post(
            "/api/my/projects",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        body = response.json()
        assert_that(
            body,
            has_entries(
                website_url="https://example.com",
                title="example.com",
                owner=has_entries(id=str(user.id)),
                creator=has_entries(id=str(user.id)),
            ),
        )
        assert_that(body["contributors"], has_length(1))
        assert_that(
            body["contributors"][0],
            has_entries(
                user=has_entries(id=str(user.id)),
                role="owner",
                full_edit=True,
            ),
        )

    def test_create_project_with_all_fields(
        self,
        client,
        user,
        auth_headers,
        tags,
    ) -> None:
        payload = {
            "website_url": "https://myproject.com",
            "title": "My Project",
            "description": "A great project",
            "tag_ids": [str(t.id) for t in tags],
        }

        response = client.post(
            "/api/my/projects",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        assert_that(
            response.json(),
            has_entries(
                title="My Project",
                description="A great project",
                tags=has_length(3),
            ),
        )


class TestGetMyProject:
    def test_get_my_project(self, client, project, auth_headers) -> None:
        response = client.get(f"/api/my/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(id=str(project.id)))


class TestUpdateProject:
    def test_update_project(self, client, project, auth_headers) -> None:
        payload = {
            "website_url": "https://updated.com",
            "title": "Updated Title",
            "description": "Updated description",
        }

        response = client.put(
            f"/api/my/projects/{project.id}",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(title="Updated Title", website_url="https://updated.com"),
        )

    def test_update_rejected_project_resets_status(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        project = ProjectFactory(
            owner=user,
            status=ProjectStatus.REJECTED,
            rejection_reason="Bad project",
        )
        payload = {
            "website_url": "https://fixed.com",
            "title": "Fixed Project",
            "description": "Updated",
        }

        response = client.put(
            f"/api/my/projects/{project.id}",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        project.refresh_from_db()
        assert_that(project.status, equal_to(ProjectStatus.PENDING))
        assert_that(project.rejection_reason, is_(none()))


class TestDeleteProject:
    def test_delete_project(self, client, project, auth_headers) -> None:
        project_id = project.id

        response = client.delete(f"/api/my/projects/{project_id}", **auth_headers)

        assert_that(response.status_code, equal_to(204))
        assert_that(Project.objects.filter(id=project_id).exists(), is_(False))


class TestResubmitProject:
    def test_resubmit_rejected_project(self, client, user, auth_headers) -> None:
        project = ProjectFactory(
            owner=user,
            status=ProjectStatus.REJECTED,
            rejection_reason="Try again",
        )

        response = client.post(
            f"/api/my/projects/{project.id}/resubmit",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        project.refresh_from_db()
        assert_that(project.status, equal_to(ProjectStatus.PENDING))
        assert_that(project.rejection_reason, is_(none()))

    def test_resubmit_non_rejected_project_fails(
        self,
        client,
        project,
        auth_headers,
    ) -> None:
        response = client.post(
            f"/api/my/projects/{project.id}/resubmit",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))


class TestPublishProject:
    def test_publish_ready_draft_returns_200_with_slug(
        self, client, user, auth_headers
    ) -> None:
        project = _ready_draft(owner=user, title="Shiny App")

        with patch("api.tasks.email.send_new_project_notification"):
            response = client.post(
                f"/api/my/projects/{project.id}/publish",
                **auth_headers,
            )

        assert_that(response.status_code, equal_to(200))
        body = response.json()
        assert_that(body, has_entries(slug="shiny-app", status="pending"))
        assert_that(body, has_key("published_at"))
        assert body["published_at"] is not None

    def test_publish_missing_description_returns_400_with_missing(
        self, client, user, auth_headers
    ) -> None:
        project = _ready_draft(owner=user, description="")

        response = client.post(
            f"/api/my/projects/{project.id}/publish",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert "description" in response.json()["missing"]
        project.refresh_from_db()
        assert_that(project.status, equal_to(ProjectStatus.DRAFT))

    def test_publish_missing_main_image_returns_400(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(
            owner=user,
            status=ProjectStatus.DRAFT,
            title="No Image",
            description="A description",
            submission_month="",
            slug=None,
            published_at=None,
        )

        response = client.post(
            f"/api/my/projects/{project.id}/publish",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(response.json()["missing"], equal_to(["main_image"]))

    def test_publish_lists_all_missing(self, client, user, auth_headers) -> None:
        project = ProjectFactory(
            owner=user,
            status=ProjectStatus.DRAFT,
            title="",
            description="",
            submission_month="",
            slug=None,
            published_at=None,
        )

        response = client.post(
            f"/api/my/projects/{project.id}/publish",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json()["missing"],
            contains_inanyorder("title", "description", "main_image"),
        )

    def test_publish_non_draft_returns_400(self, client, user, auth_headers) -> None:
        project = ProjectFactory(
            owner=user, status=ProjectStatus.PENDING, title="Already Published"
        )

        response = client.post(
            f"/api/my/projects/{project.id}/publish",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(400))

    def test_publish_non_owner_returns_404(self, client, auth_headers) -> None:
        project = _ready_draft()  # owned by a different user

        response = client.post(
            f"/api/my/projects/{project.id}/publish",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))

    def test_publish_requires_auth(self, client) -> None:
        response = client.post(
            "/api/my/projects/00000000-0000-0000-0000-000000000000/publish"
        )

        assert_that(response.status_code, equal_to(401))


class TestAuthentication:
    """401 tests - unauthenticated users should not access any endpoints."""

    def test_list_projects_requires_auth(self, client) -> None:
        response = client.get("/api/my/projects")
        assert_that(response.status_code, equal_to(401))

    def test_create_project_requires_auth(self, client) -> None:
        response = client.post(
            "/api/my/projects",
            data=json.dumps({"url": "https://example.com"}),
            content_type="application/json",
        )
        assert_that(response.status_code, equal_to(401))

    def test_get_project_requires_auth(self, client, project) -> None:
        response = client.get(f"/api/my/projects/{project.id}")
        assert_that(response.status_code, equal_to(401))

    def test_update_project_requires_auth(self, client, project) -> None:
        response = client.put(
            f"/api/my/projects/{project.id}",
            data=json.dumps({"url": "https://example.com"}),
            content_type="application/json",
        )
        assert_that(response.status_code, equal_to(401))

    def test_delete_project_requires_auth(self, client, project) -> None:
        response = client.delete(f"/api/my/projects/{project.id}")
        assert_that(response.status_code, equal_to(401))

    def test_resubmit_project_requires_auth(self, client, project) -> None:
        response = client.post(f"/api/my/projects/{project.id}/resubmit")
        assert_that(response.status_code, equal_to(401))


class TestAuthorization:
    """403/404 tests - users should not access other users' projects."""

    def test_get_other_users_project_returns_404(
        self,
        client,
        other_project,
        auth_headers,
    ) -> None:
        response = client.get(f"/api/my/projects/{other_project.id}", **auth_headers)
        assert_that(response.status_code, equal_to(404))

    def test_update_other_users_project_returns_404(
        self,
        client,
        other_project,
        auth_headers,
    ) -> None:
        response = client.put(
            f"/api/my/projects/{other_project.id}",
            data=json.dumps({"website_url": "https://hacked.com"}),
            content_type="application/json",
            **auth_headers,
        )
        assert_that(response.status_code, equal_to(404))

    def test_delete_other_users_project_returns_404(
        self,
        client,
        other_project,
        auth_headers,
    ) -> None:
        response = client.delete(f"/api/my/projects/{other_project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(404))
        assert_that(Project.objects.filter(id=other_project.id).exists(), is_(True))

    def test_resubmit_other_users_project_returns_404(
        self,
        client,
        other_user,
        auth_headers,
    ) -> None:
        project = ProjectFactory(owner=other_user, status=ProjectStatus.REJECTED)

        response = client.post(
            f"/api/my/projects/{project.id}/resubmit",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))


class TestNonCreatorContributorAccess:
    def test_full_edit_contributor_can_list_project(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.SUGGESTER,
            full_edit=True,
        )

        response = client.get("/api/my/projects", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        ids = [item["id"] for item in response.json()]
        assert_that(ids, equal_to([str(project.id)]))

    def test_full_edit_contributor_can_get_project(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.SUGGESTER,
            full_edit=True,
        )

        response = client.get(f"/api/my/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(id=str(project.id)))

    def test_full_edit_contributor_can_update_project(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(title="Original")
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.SUGGESTER,
            full_edit=True,
        )
        payload = {
            "website_url": "https://updated.com",
            "title": "Suggested Edit",
            "description": "Updated description",
        }

        response = client.put(
            f"/api/my/projects/{project.id}",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(200))
        project.refresh_from_db()
        assert_that(project.title, equal_to("Suggested Edit"))

    def test_contributor_without_full_edit_returns_404(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory()
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.SUGGESTER,
            full_edit=False,
        )

        response = client.get(f"/api/my/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(404))

    def test_contributor_without_full_edit_cannot_update(
        self, client, user, auth_headers
    ) -> None:
        project = ProjectFactory(title="Original")
        ProjectContributor.objects.create(
            project=project,
            user=user,
            role=ContributorRole.SUGGESTER,
            full_edit=False,
        )

        response = client.put(
            f"/api/my/projects/{project.id}",
            data=json.dumps({"website_url": "https://hacked.com", "title": "Hacked"}),
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(404))
        project.refresh_from_db()
        assert_that(project.title, equal_to("Original"))
