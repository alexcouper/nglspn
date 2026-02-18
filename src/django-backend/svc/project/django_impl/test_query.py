from uuid import uuid4

import pytest

from apps.projects.models import ProjectStatus
from svc.project.django_impl import DjangoProjectQuery
from svc.project.exceptions import ProjectNotFoundError
from tests.factories import ProjectFactory, UserFactory

query = DjangoProjectQuery()


@pytest.mark.django_db
class TestGetById:
    def test_returns_existing_project(self):
        project = ProjectFactory()

        result = query.get_by_id(project.id)

        assert result.id == project.id
        assert result.title == project.title

    def test_raises_for_nonexistent_project(self):
        with pytest.raises(ProjectNotFoundError):
            query.get_by_id(uuid4())


@pytest.mark.django_db
class TestGetForOwner:
    def test_returns_project_owned_by_user(self):
        user = UserFactory()
        project = ProjectFactory(owner=user)

        result = query.get_for_owner(project.id, user.id)

        assert result.id == project.id

    def test_raises_when_not_owner(self):
        project = ProjectFactory()
        other_user = UserFactory()

        with pytest.raises(ProjectNotFoundError):
            query.get_for_owner(project.id, other_user.id)


@pytest.mark.django_db
class TestListApproved:
    def test_returns_only_approved_projects(self):
        ProjectFactory(status=ProjectStatus.APPROVED)
        ProjectFactory(status=ProjectStatus.PENDING)

        result = query.list_approved()

        assert result["total"] == 1

    def test_paginates_results(self):
        for _ in range(3):
            ProjectFactory(status=ProjectStatus.APPROVED)

        result = query.list_approved(per_page=2, page=1)

        assert len(result["projects"]) == 2
        assert result["total"] == 3
        assert result["pages"] == 2


@pytest.mark.django_db
class TestListForOwner:
    def test_returns_all_projects_for_owner(self):
        user = UserFactory()
        ProjectFactory(owner=user)
        ProjectFactory(owner=user)
        ProjectFactory()  # different owner

        result = query.list_for_owner(user.id)

        assert result.count() == 2


@pytest.mark.django_db
class TestCountPending:
    def test_counts_pending_projects(self):
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.PENDING)
        ProjectFactory(status=ProjectStatus.APPROVED)

        assert query.count_pending() == 2
