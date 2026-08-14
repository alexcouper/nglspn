from unittest.mock import patch
from uuid import uuid4

import pytest

from apps.projects.models import (
    CompetitionEntry,
    CompetitionStatus,
    ContributorRole,
    EntrySource,
    Project,
    ProjectContributor,
    ProjectStatus,
)
from services import REPO
from services.project.django_impl import DjangoProjectHandler
from services.project.exceptions import (
    InvalidCompetitionError,
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
        assert project.creator_id == user.id
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

    def test_tipoff_create_attaches_seed_owner_and_tipster(self):
        user = UserFactory()
        data = CreateProjectInput(
            owner_id=user.id,
            website_url="https://example.com",
            title="Community Submitted",
            is_community_tipoff=True,
        )

        project = handler.create(data)

        assert project.creator_id == user.id
        contributors = list(project.contributors.all())
        assert len(contributors) == 2
        seed = REPO.users.get_community_user()
        seed_owner = next(c for c in contributors if c.role == ContributorRole.OWNER)
        tipster = next(c for c in contributors if c.role == ContributorRole.TIPSTER)
        assert seed_owner.user_id == seed.id
        assert seed_owner.full_edit is True
        assert tipster.user_id == user.id
        assert tipster.full_edit is True

    def test_tipoff_create_rolls_back_atomically(self):
        user = UserFactory()
        data = CreateProjectInput(
            owner_id=user.id,
            website_url="https://example.com",
            title="Atomic Community",
            is_community_tipoff=True,
        )

        original_create = ProjectContributor.objects.create
        call_count = {"n": 0}

        def flaky_create(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                msg = "forced"
                raise RuntimeError(msg)
            return original_create(*args, **kwargs)

        with (
            patch.object(
                ProjectContributor.objects,
                "create",
                side_effect=flaky_create,
            ),
            pytest.raises(RuntimeError),
        ):
            handler.create(data)

        assert not Project.objects.filter(title="Atomic Community").exists()
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

    def test_publish_enters_no_competition(self):
        """Publishing used to add the project to the open round as a side
        effect. It now publishes and nothing else — entry is its own call."""
        user = UserFactory()
        competition = CompetitionFactory(
            status=CompetitionStatus.ACCEPTING_APPLICATIONS
        )
        project = _ready_draft(owner=user)

        with patch("api.tasks.email.send_new_project_notification"):
            handler.publish(project.id, user.id)

        assert project not in competition.projects.all()
        assert CompetitionEntry.objects.count() == 0

    def test_publish_without_open_competition_still_succeeds(self):
        user = UserFactory()
        project = _ready_draft(owner=user)

        with patch("api.tasks.email.send_new_project_notification"):
            result = handler.publish(project.id, user.id)

        assert result.status == ProjectStatus.PENDING

    def test_publish_tipoff_enters_no_competition_either(self):
        user = UserFactory()
        competition = CompetitionFactory(
            status=CompetitionStatus.ACCEPTING_APPLICATIONS
        )
        # Build a draft via the handler so the contributor wiring matches the
        # real tip-off shape (seed user as OWNER + user as TIPSTER).
        data = CreateProjectInput(
            owner_id=user.id,
            website_url="https://example.com",
            title="Community Pub",
            description="A community tip-off project",
            is_community_tipoff=True,
        )
        project = handler.create(data)
        # Bring the draft up to publish-ready state.
        project.status = ProjectStatus.DRAFT
        project.save(update_fields=["status"])
        ProjectImageFactory(project=project, is_main=True, upload_status="uploaded")

        with patch("api.tasks.email.send_new_project_notification"):
            result = handler.publish(project.id, user.id)

        assert result.status == ProjectStatus.PENDING
        assert project not in competition.projects.all()

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


@pytest.mark.django_db
class TestEnterCompetition:
    def _open(self, **kwargs):
        return CompetitionFactory(
            status=CompetitionStatus.ACCEPTING_APPLICATIONS, **kwargs
        )

    def test_entering_records_the_contributor_and_the_route(self):
        user = UserFactory()
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)
        competition = self._open()

        handler.enter_competition(project.id, competition.id, user.id)

        entry = CompetitionEntry.objects.get()
        assert entry.competition_id == competition.id
        assert entry.entered_via == EntrySource.MANUAL
        assert entry.entered_by_id == user.id

    def test_a_draft_is_rejected_before_eligibility_is_considered(self):
        user = UserFactory()
        project = ProjectFactory(owner=user, status=ProjectStatus.DRAFT)
        competition = self._open()

        with pytest.raises(InvalidProjectStateError):
            handler.enter_competition(project.id, competition.id, user.id)

        assert CompetitionEntry.objects.count() == 0

    def test_a_competition_that_is_not_open_is_rejected(self):
        user = UserFactory()
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)
        competition = CompetitionFactory(status=CompetitionStatus.VOTING)

        with pytest.raises(InvalidCompetitionError):
            handler.enter_competition(project.id, competition.id, user.id)

    def test_a_second_competition_in_the_same_series_is_rejected(self):
        user = UserFactory()
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)
        CompetitionEntry.objects.create(
            competition=CompetitionFactory(entry_series="monthly"),
            project=project,
            entered_via=EntrySource.MANUAL,
        )
        july = self._open(entry_series="monthly")

        with pytest.raises(InvalidCompetitionError):
            handler.enter_competition(project.id, july.id, user.id)

        assert CompetitionEntry.objects.count() == 1

    def test_a_different_series_is_allowed(self):
        user = UserFactory()
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)
        CompetitionEntry.objects.create(
            competition=CompetitionFactory(entry_series="monthly"),
            project=project,
            entered_via=EntrySource.MANUAL,
        )
        hackathon = self._open(entry_series="summer-hackathon")

        handler.enter_competition(project.id, hackathon.id, user.id)

        assert CompetitionEntry.objects.count() == 2

    def test_a_non_contributor_cannot_enter(self):
        project = ProjectFactory(status=ProjectStatus.PENDING)
        competition = self._open()

        with pytest.raises(ProjectNotFoundError):
            handler.enter_competition(project.id, competition.id, UserFactory().id)

    def test_an_unknown_competition_is_rejected(self):
        user = UserFactory()
        project = ProjectFactory(owner=user, status=ProjectStatus.PENDING)

        with pytest.raises(InvalidCompetitionError):
            handler.enter_competition(project.id, uuid4(), user.id)
