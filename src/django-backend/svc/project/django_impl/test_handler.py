import pytest

from apps.projects.models import Project, ProjectStatus
from svc.project.django_impl import DjangoProjectHandler
from svc.project.exceptions import ProjectNotFoundError
from svc.project.handler_interface import CreateProjectInput, UpdateProjectInput
from tests.factories import ProjectFactory, TagFactory, UserFactory

handler = DjangoProjectHandler()


@pytest.mark.django_db
class TestCreate:
    def test_creates_project_with_required_fields(self):
        user = UserFactory()
        data = CreateProjectInput(
            owner_id=user.id,
            website_url="https://example.com",
            title="My Project",
            description="A cool project",
        )

        project = handler.create(data)

        assert project.title == "My Project"
        assert project.owner_id == user.id
        assert project.website_url == "https://example.com"
        assert project.status == ProjectStatus.PENDING

    def test_derives_title_from_url_when_not_provided(self):
        user = UserFactory()
        data = CreateProjectInput(
            owner_id=user.id,
            website_url="https://example.com",
        )

        project = handler.create(data)

        assert project.title == "example.com"

    def test_creates_project_with_tags(self):
        user = UserFactory()
        tag = TagFactory()
        data = CreateProjectInput(
            owner_id=user.id,
            website_url="https://example.com",
            title="Tagged Project",
            tag_ids=[tag.id],
        )

        project = handler.create(data)

        assert tag in project.tags.all()


@pytest.mark.django_db
class TestUpdate:
    def test_updates_project_fields(self):
        user = UserFactory()
        project = ProjectFactory(owner=user, title="Old Title")
        data = UpdateProjectInput(
            website_url="https://new.example.com",
            title="New Title",
        )

        updated = handler.update(project.id, user.id, data)

        assert updated.title == "New Title"
        assert updated.website_url == "https://new.example.com"

    def test_raises_when_not_owner(self):
        project = ProjectFactory()
        other_user = UserFactory()
        data = UpdateProjectInput(website_url="https://example.com")

        with pytest.raises(ProjectNotFoundError):
            handler.update(project.id, other_user.id, data)


@pytest.mark.django_db
class TestDelete:
    def test_deletes_owned_project(self):
        user = UserFactory()
        project = ProjectFactory(owner=user)

        handler.delete(project.id, user.id)

        assert not Project.objects.filter(id=project.id).exists()

    def test_raises_when_not_owner(self):
        project = ProjectFactory()
        other_user = UserFactory()

        with pytest.raises(ProjectNotFoundError):
            handler.delete(project.id, other_user.id)


@pytest.mark.django_db
class TestResubmit:
    def test_resubmits_rejected_project(self):
        user = UserFactory()
        project = ProjectFactory(
            owner=user,
            status=ProjectStatus.REJECTED,
            rejection_reason="Needs work",
        )

        result = handler.resubmit(project.id, user.id)

        assert result.status == ProjectStatus.PENDING
        assert result.rejection_reason is None
