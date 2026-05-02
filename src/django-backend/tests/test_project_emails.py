from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, override_settings
from django.urls import reverse

from api.tasks import email as email_tasks
from apps.emails.models import SentEmail, SentEmailType
from apps.projects.admin import ProjectAdmin
from apps.projects.models import (
    ContributorRole,
    Project,
    ProjectContributor,
    ProjectStatus,
)
from services import HANDLERS, REPO

from .factories import ProjectFactory, UserFactory


@pytest.mark.django_db
class TestApproveProjectsAdminAction:
    def _call_action(self, projects, user=None):
        admin_user = user or UserFactory(is_superuser=True, is_staff=True)
        site = AdminSite()
        model_admin = ProjectAdmin(Project, site)
        request = RequestFactory().post("/admin/projects/project/")
        request.user = admin_user
        request.session = "session"
        request._messages = FallbackStorage(request)  # noqa: SLF001
        queryset = Project.objects.filter(pk__in=[p.pk for p in projects])
        model_admin.approve_projects(request, queryset)

    def test_sends_email_for_each_approved_project(self):
        projects = ProjectFactory.create_batch(2)

        with patch.object(HANDLERS.email, "send_project_approved_email") as mock_send:
            self._call_action(projects)

        assert mock_send.call_count == 2

    def test_does_not_send_email_for_non_pending_projects(self):
        approved_project = ProjectFactory(status=ProjectStatus.APPROVED)

        with patch.object(HANDLERS.email, "send_project_approved_email") as mock_send:
            self._call_action([approved_project])

        mock_send.assert_not_called()

    def test_continues_approval_on_email_failure(self):
        projects = ProjectFactory.create_batch(2)

        with patch.object(
            HANDLERS.email,
            "send_project_approved_email",
            side_effect=Exception("SMTP error"),
        ):
            self._call_action(projects)

        for project in projects:
            project.refresh_from_db()
            assert project.status == ProjectStatus.APPROVED


@pytest.mark.django_db
class TestSendProjectApprovedEmailTask:
    def test_sends_one_email_per_full_edit_contributor(self):
        project = ProjectFactory()
        creator = project.creator
        extra_full_edit = UserFactory()
        ProjectContributor.objects.create(
            project=project,
            user=extra_full_edit,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )
        no_edit = UserFactory()
        ProjectContributor.objects.create(
            project=project,
            user=no_edit,
            role=ContributorRole.TIPSTER,
            full_edit=False,
        )

        with patch.object(HANDLERS.email, "send_project_approved_email") as mock_send:
            email_tasks.send_project_approved_email.call(str(project.id))

        recipients = {call.args[1].id for call in mock_send.call_args_list}
        assert mock_send.call_count == 2
        assert recipients == {creator.id, extra_full_edit.id}
        assert no_edit.id not in recipients

    def test_does_not_send_when_no_full_edit_contributors(self):
        project = ProjectFactory()
        ProjectContributor.objects.filter(project=project).update(full_edit=False)

        with patch.object(HANDLERS.email, "send_project_approved_email") as mock_send:
            email_tasks.send_project_approved_email.call(str(project.id))

        mock_send.assert_not_called()

    def test_does_not_send_to_system_user_contributor(self):
        # Community tip-off project: seed user is OWNER (full_edit=True),
        # real user is TIPSTER (full_edit=True). Approval email must skip
        # the seed account.
        tipster = UserFactory()
        seed = REPO.users.get_community_user()
        project = ProjectFactory(creator=tipster, _contributor=False)
        ProjectContributor.objects.create(
            project=project, user=seed, role=ContributorRole.OWNER, full_edit=True
        )
        ProjectContributor.objects.create(
            project=project,
            user=tipster,
            role=ContributorRole.TIPSTER,
            full_edit=True,
        )

        with patch.object(HANDLERS.email, "send_project_approved_email") as mock_send:
            email_tasks.send_project_approved_email.call(str(project.id))

        recipients = {call.args[1].id for call in mock_send.call_args_list}
        assert recipients == {tipster.id}
        assert seed.id not in recipients


@pytest.mark.django_db
class TestSendNewProjectNotificationTask:
    @override_settings(NEW_PROJECT_NOTIFICATION_EMAIL="")
    def test_noop_when_recipient_not_configured(self):
        project = ProjectFactory()

        with patch.object(HANDLERS.email, "send_new_project_notification") as mock_send:
            email_tasks.send_new_project_notification.call(str(project.id))

        mock_send.assert_not_called()

    @override_settings(NEW_PROJECT_NOTIFICATION_EMAIL="admin@example.com")
    def test_calls_handler_with_project_and_recipient(self):
        project = ProjectFactory()

        with patch.object(HANDLERS.email, "send_new_project_notification") as mock_send:
            email_tasks.send_new_project_notification.call(str(project.id))

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args.args[0].id == project.id
        assert call_args.args[1] == "admin@example.com"


def _approved_project(**kwargs) -> Project:
    return ProjectFactory(status=ProjectStatus.APPROVED, **kwargs)


def _record_prior_approval_email(
    project: Project, *, success: bool = True
) -> SentEmail:
    return SentEmail.objects.create(
        recipient=project.creator,
        project=project,
        email_type=SentEmailType.PROJECT_APPROVED,
        subject="Your project has been approved - Naglasúpan",
        to_email=project.creator.email,
        success=success,
    )


@pytest.mark.django_db
class TestProjectApprovalEmailAdminViews:
    def _preview_url(self, project: Project) -> str:
        return reverse(
            "admin:projects_project_preview_approval_email",
            args=[project.pk],
        )

    def _send_url(self, project: Project) -> str:
        return reverse(
            "admin:projects_project_send_approval_email",
            args=[project.pk],
        )

    def test_preview_renders_project_approved_template(self, admin_client):
        project = _approved_project(title="Naglarokk")
        project.creator.first_name = "Stefán"
        project.creator.save(update_fields=["first_name"])

        response = admin_client.get(self._preview_url(project))

        assert response.status_code == 200
        body = response.content.decode()
        assert "Naglarokk" in body
        assert "Stefán" in body

    def test_send_get_shows_confirm_for_approved_project(self, admin_client):
        project = _approved_project()

        response = admin_client.get(self._send_url(project))

        assert response.status_code == 200
        assert b"Send approval email" in response.content
        assert project.creator.email.encode() in response.content

    def test_send_get_warns_when_already_successfully_sent(self, admin_client):
        project = _approved_project()
        _record_prior_approval_email(project, success=True)

        response = admin_client.get(self._send_url(project))

        assert response.status_code == 200
        assert b"already received" in response.content

    def test_send_get_no_warning_when_no_prior_send(self, admin_client):
        project = _approved_project()

        response = admin_client.get(self._send_url(project))

        assert response.status_code == 200
        assert b"already received" not in response.content

    def test_send_get_no_warning_when_only_failed_prior_sends(self, admin_client):
        project = _approved_project()
        _record_prior_approval_email(project, success=False)

        response = admin_client.get(self._send_url(project))

        assert response.status_code == 200
        assert b"already received" not in response.content

    def test_send_get_no_warning_when_prior_send_was_for_different_project(
        self, admin_client
    ):
        creator = UserFactory()
        other_project = _approved_project(creator=creator)
        _record_prior_approval_email(other_project, success=True)
        target_project = _approved_project(creator=creator)

        response = admin_client.get(self._send_url(target_project))

        assert response.status_code == 200
        assert b"already received" not in response.content

    def test_send_post_enqueues_task_for_approved_project(self, admin_client):
        project = _approved_project()

        with patch.object(HANDLERS.email, "send_project_approved_email") as mock_send:
            response = admin_client.post(self._send_url(project))

        assert response.status_code == 302
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args.args[0].id == project.id
        assert call_args.args[1].id == project.creator.id

    def test_send_post_redirects_to_change_view(self, admin_client):
        project = _approved_project()

        with patch.object(HANDLERS.email, "send_project_approved_email"):
            response = admin_client.post(self._send_url(project))

        expected = reverse("admin:projects_project_change", args=[project.pk])
        assert response.url == expected

    def test_send_rejects_pending_project(self, admin_client):
        project = ProjectFactory(status=ProjectStatus.PENDING)

        with patch.object(HANDLERS.email, "send_project_approved_email") as mock_send:
            get_response = admin_client.get(self._send_url(project))
            post_response = admin_client.post(self._send_url(project))

        assert get_response.status_code == 302
        assert post_response.status_code == 302
        mock_send.assert_not_called()

    def test_send_rejects_rejected_project(self, admin_client):
        project = ProjectFactory(status=ProjectStatus.REJECTED)

        with patch.object(HANDLERS.email, "send_project_approved_email") as mock_send:
            response = admin_client.post(self._send_url(project))

        assert response.status_code == 302
        mock_send.assert_not_called()

    def test_change_view_exposes_button_urls_when_approved(self, admin_client):
        project = _approved_project()

        url = reverse("admin:projects_project_change", args=[project.pk])
        response = admin_client.get(url)

        assert response.status_code == 200
        assert self._preview_url(project).encode() in response.content
        assert self._send_url(project).encode() in response.content

    def test_change_view_hides_button_urls_when_pending(self, admin_client):
        project = ProjectFactory(status=ProjectStatus.PENDING)

        url = reverse("admin:projects_project_change", args=[project.pk])
        response = admin_client.get(url)

        assert response.status_code == 200
        assert self._send_url(project).encode() not in response.content
