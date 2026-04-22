import json

from hamcrest import assert_that, equal_to, has_entries, has_length, is_, none

from apps.projects.models import Project, ProjectStatus
from tests.factories import ProjectFactory


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
        assert_that(
            response.json(),
            has_entries(
                website_url="https://example.com",
                title="example.com",
                owner=has_entries(id=str(user.id)),
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
