from unittest.mock import patch

import pytest

from apps.projects.models import (
    CompetitionStatus,
    ContributorRole,
    Project,
    ProjectContributor,
    ProjectStatus,
)
from services.project.django_impl import DjangoProjectHandler
from services.project.exceptions import (
    InvalidProjectStateError,
    ProjectNotFoundError,
    PublishPreconditionsError,
)
from services.project.handler_interface import CreateProjectInput, UpdateProjectInput
from tests.factories import (
    CompetitionFactory,
    ProjectFactory,
    ProjectImageFactory,
    TagFactory,
    UserFactory,
)

handler = DjangoProjectHandler()


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
        assert project.status == ProjectStatus.DRAFT

    def test_creates_owner_contributor(self):
        user = UserFactory()
        data = CreateProjectInput(
            owner_id=user.id,
            website_url="https://example.com",
            title="My Project",
        )

        project = handler.create(data)

        contributors = list(project.contributors.all())
        assert len(contributors) == 1
        assert contributors[0].user_id == user.id
        assert contributors[0].role == ContributorRole.OWNER
        assert contributors[0].full_edit is True

    def test_create_rolls_back_when_contributor_insert_fails(self):
        user = UserFactory()
        data = CreateProjectInput(
            owner_id=user.id,
            website_url="https://example.com",
            title="Atomic",
        )

        with (
            patch.object(
                ProjectContributor.objects,
                "create",
                side_effect=RuntimeError("forced"),
            ),
            pytest.raises(RuntimeError),
        ):
            handler.create(data)

        assert not Project.objects.filter(title="Atomic").exists()
        assert not ProjectContributor.objects.filter(user_id=user.id).exists()

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

    def test_create_does_not_enqueue_admin_notification(self):
        user = UserFactory()
        data = CreateProjectInput(
            owner_id=user.id,
            website_url="https://example.com",
            title="Quiet Create",
        )

        with patch("api.tasks.email.send_new_project_notification") as mock_task:
            handler.create(data)

        mock_task.enqueue.assert_not_called()

    def test_create_leaves_submission_month_and_slug_blank(self):
        user = UserFactory()
        data = CreateProjectInput(
            owner_id=user.id,
            website_url="https://example.com",
            title="Fresh Draft",
        )

        project = handler.create(data)

        assert project.submission_month == ""
        assert project.slug is None
        assert project.published_at is None

    def test_create_does_not_assign_to_open_competition(self):
        user = UserFactory()
        competition = CompetitionFactory(
            status=CompetitionStatus.ACCEPTING_APPLICATIONS
        )
        data = CreateProjectInput(
            owner_id=user.id,
            website_url="https://example.com",
            title="No Auto Join",
        )

        project = handler.create(data)

        assert project not in competition.projects.all()


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


@pytest.mark.django_db
class TestPublish:
    def test_publish_ready_draft_transitions_and_sets_metadata(self):
        user = UserFactory()
        project = _ready_draft(owner=user, title="Ready App")

        with patch("api.tasks.email.send_new_project_notification") as mock_task:
            result = handler.publish(project.id, user.id)

        assert result.status == ProjectStatus.PENDING
        assert result.slug == "ready-app"
        assert result.published_at is not None
        assert result.submission_month != ""
        mock_task.enqueue.assert_called_once_with(str(result.id))

    def test_publish_adds_to_open_competition(self):
        user = UserFactory()
        competition = CompetitionFactory(
            status=CompetitionStatus.ACCEPTING_APPLICATIONS
        )
        project = _ready_draft(owner=user)

        with patch("api.tasks.email.send_new_project_notification"):
            handler.publish(project.id, user.id)

        assert project in competition.projects.all()

    def test_publish_without_open_competition_still_succeeds(self):
        user = UserFactory()
        project = _ready_draft(owner=user)

        with patch("api.tasks.email.send_new_project_notification"):
            result = handler.publish(project.id, user.id)

        assert result.status == ProjectStatus.PENDING

    def test_publish_missing_title_raises(self):
        user = UserFactory()
        project = _ready_draft(owner=user, title="")

        with (
            patch("api.tasks.email.send_new_project_notification") as mock_task,
            pytest.raises(PublishPreconditionsError) as exc,
        ):
            handler.publish(project.id, user.id)

        assert "title" in exc.value.missing
        project.refresh_from_db()
        assert project.status == ProjectStatus.DRAFT
        mock_task.enqueue.assert_not_called()

    def test_publish_missing_description_raises(self):
        user = UserFactory()
        project = _ready_draft(owner=user, description="")

        with pytest.raises(PublishPreconditionsError) as exc:
            handler.publish(project.id, user.id)

        assert "description" in exc.value.missing

    def test_publish_missing_main_image_raises(self):
        user = UserFactory()
        project = ProjectFactory(
            owner=user,
            status=ProjectStatus.DRAFT,
            title="No Image",
            description="Has description",
            submission_month="",
            slug=None,
            published_at=None,
        )

        with pytest.raises(PublishPreconditionsError) as exc:
            handler.publish(project.id, user.id)

        assert exc.value.missing == ["main_image"]

    def test_publish_lists_all_missing_fields(self):
        user = UserFactory()
        project = ProjectFactory(
            owner=user,
            status=ProjectStatus.DRAFT,
            title="",
            description="",
            submission_month="",
            slug=None,
            published_at=None,
        )

        with pytest.raises(PublishPreconditionsError) as exc:
            handler.publish(project.id, user.id)

        assert set(exc.value.missing) == {"title", "description", "main_image"}

    def test_publish_non_draft_raises_invalid_state(self):
        user = UserFactory()
        project = _ready_draft(owner=user)
        project.status = ProjectStatus.PENDING
        project.save(update_fields=["status"])

        with pytest.raises(InvalidProjectStateError):
            handler.publish(project.id, user.id)

    def test_publish_by_non_owner_raises_not_found(self):
        project = _ready_draft()
        other = UserFactory()

        with pytest.raises(ProjectNotFoundError):
            handler.publish(project.id, other.id)

    def test_publish_rolls_back_slug_when_status_save_fails(self):
        user = UserFactory()
        project = _ready_draft(owner=user, title="Atomic Publish")

        real_save = Project.save
        calls = {"n": 0}

        def flaky_save(self, *args, **kwargs):
            calls["n"] += 1
            # First save() = slug assignment inside assign_unique_slug;
            # second save() = status/published_at/submission_month write.
            if calls["n"] == 2:
                msg = "simulated failure on status save"
                raise RuntimeError(msg)
            return real_save(self, *args, **kwargs)

        with (
            patch.object(Project, "save", flaky_save),
            pytest.raises(RuntimeError, match="simulated failure"),
        ):
            handler.publish(project.id, user.id)

        project.refresh_from_db()
        assert project.slug is None
        assert project.status == ProjectStatus.DRAFT
        assert project.published_at is None
        assert project.submission_month == ""

    def test_publish_generates_collision_safe_slug(self):
        user = UserFactory()
        ProjectFactory(
            title="Duplicate", slug="duplicate", status=ProjectStatus.APPROVED
        )
        project = _ready_draft(owner=user, title="Duplicate")

        with patch("api.tasks.email.send_new_project_notification"):
            result = handler.publish(project.id, user.id)

        assert result.slug == "duplicate-2"
