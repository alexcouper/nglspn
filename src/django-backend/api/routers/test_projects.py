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

    def test_sort_by_rejects_invalid_field(self, client) -> None:
        response = client.get("/api/projects?sort_by=nonexistent")

        assert_that(response.status_code, equal_to(400))

    def test_sort_by_rejects_related_field_traversal(self, client) -> None:
        response = client.get("/api/projects?sort_by=owner__email")

        assert_that(response.status_code, equal_to(400))

    def test_sort_by_accepts_valid_fields(self, client) -> None:
        ProjectFactory(status=ProjectStatus.APPROVED)

        for field in ["created_at", "title"]:
            response = client.get(f"/api/projects?sort_by={field}")
            assert_that(response.status_code, equal_to(200))


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


@pytest.mark.django_db
class TestGetProjectByIdentifier:
    def test_lookup_by_slug(self, client) -> None:
        project = ProjectFactory(
            status=ProjectStatus.APPROVED, slug="cool-app", title="Cool App"
        )

        response = client.get("/api/projects/cool-app")

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json(),
            has_entries(id=str(project.id), slug="cool-app"),
        )

    def test_lookup_by_uuid_returns_canonical_slug(self, client) -> None:
        project = ProjectFactory(
            status=ProjectStatus.APPROVED, slug="cool-app", title="Cool App"
        )

        response = client.get(f"/api/projects/{project.id}")

        assert_that(response.status_code, equal_to(200))
        assert_that(response.json(), has_entries(slug="cool-app"))

    def test_unknown_identifier_returns_404(self, client) -> None:
        response = client.get("/api/projects/does-not-exist")

        assert_that(response.status_code, equal_to(404))

    def test_draft_not_visible_to_anonymous(self, client) -> None:
        project = ProjectFactory(
            status=ProjectStatus.DRAFT, slug=None, title="Hidden Draft"
        )

        response = client.get(f"/api/projects/{project.id}")

        assert_that(response.status_code, equal_to(404))


@pytest.mark.django_db
class TestDraftExclusionFromListings:
    def test_drafts_excluded_from_main_list(self, client) -> None:
        ProjectFactory(status=ProjectStatus.APPROVED, title="Shown")
        ProjectFactory(status=ProjectStatus.DRAFT, title="Hidden")

        response = client.get("/api/projects")

        assert_that(response.status_code, equal_to(200))
        titles = [p["title"] for p in response.json()["projects"]]
        assert "Shown" in titles
        assert "Hidden" not in titles

    def test_drafts_not_counted_in_pending_total(self, client) -> None:
        ProjectFactory(status=ProjectStatus.DRAFT)
        ProjectFactory(status=ProjectStatus.PENDING)

        response = client.get("/api/projects")

        assert_that(response.json()["pending_projects_count"], equal_to(1))
