import pytest
from hamcrest import assert_that, equal_to, has_entries

from api.auth.jwt import create_access_token
from apps.projects.models import ProjectStatus
from tests.factories import ProjectFactory, UserFactory


@pytest.mark.django_db
class TestListProjects:
    def test_list_projects_includes_pending_projects_count(self, client) -> None:
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.APPROVED)
        ProjectFactory(status=ProjectStatus.REJECTED)

        response = client.get("/api/projects")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json()["pending_projects_count"], equal_to(2))


@pytest.mark.django_db
class TestGetPublicProject:
    def test_anonymous_user_can_access_approved_project(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.APPROVED)

        response = client.get(f"/api/projects/{project.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                id=str(project.id),
                title=project.title,
            ),
        )

    def test_authenticated_user_can_access_approved_project(
        self,
        client,
        auth_headers,
    ) -> None:
        other_owner = UserFactory()
        project = ProjectFactory(owner=other_owner, status=ProjectStatus.APPROVED)

        response = client.get(f"/api/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                id=str(project.id),
                title=project.title,
            ),
        )

    def test_owner_can_access_own_pending_project(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)

        response = client.get(f"/api/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                id=str(project.id),
                title=project.title,
            ),
        )

    def test_owner_can_access_own_rejected_project(
        self,
        client,
        user,
        auth_headers,
    ) -> None:
        project = ProjectFactory(owner=user, status=ProjectStatus.REJECTED)

        response = client.get(f"/api/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                id=str(project.id),
                title=project.title,
            ),
        )

    def test_anonymous_user_cannot_access_pending_project(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.PENDING)

        response = client.get(f"/api/projects/{project.id}")

        assert_that(response.status_code, equal_to(404))

    def test_anonymous_user_cannot_access_rejected_project(self, client) -> None:
        project = ProjectFactory(status=ProjectStatus.REJECTED)

        response = client.get(f"/api/projects/{project.id}")

        assert_that(response.status_code, equal_to(404))

    def test_other_user_cannot_access_pending_project(
        self,
        client,
        auth_headers,
    ) -> None:
        other_owner = UserFactory()
        project = ProjectFactory(owner=other_owner, status=ProjectStatus.PENDING)

        response = client.get(f"/api/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(404))

    def test_other_user_cannot_access_rejected_project(
        self,
        client,
        auth_headers,
    ) -> None:
        other_owner = UserFactory()
        project = ProjectFactory(owner=other_owner, status=ProjectStatus.REJECTED)

        response = client.get(f"/api/projects/{project.id}", **auth_headers)

        assert_that(response.status_code, equal_to(404))

    def test_nonexistent_project_returns_404(self, client) -> None:
        response = client.get("/api/projects/00000000-0000-0000-0000-000000000000")

        assert_that(response.status_code, equal_to(404))

    def test_admin_can_access_pending_project(self, client) -> None:
        admin = UserFactory(is_superuser=True)

        token = create_access_token(admin.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        project = ProjectFactory(status=ProjectStatus.PENDING)

        response = client.get(f"/api/projects/{project.id}", **headers)

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(
                id=str(project.id),
                title=project.title,
            ),
        )
