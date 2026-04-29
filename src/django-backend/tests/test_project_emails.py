from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, override_settings

from api.tasks import email as email_tasks
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
            role=ContributorRole.SUGGESTER,
            full_edit=True,
        )
        no_edit = UserFactory()
        ProjectContributor.objects.create(
            project=project,
            user=no_edit,
            role=ContributorRole.SUGGESTER,
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
        # Community-suggested project: seed user is OWNER (full_edit=True),
        # real user is SUGGESTER (full_edit=True). Approval email must skip
        # the seed account.
        suggester = UserFactory()
        seed = REPO.users.get_community_user()
        project = ProjectFactory(creator=suggester, _contributor=False)
        ProjectContributor.objects.create(
            project=project, user=seed, role=ContributorRole.OWNER, full_edit=True
        )
        ProjectContributor.objects.create(
            project=project,
            user=suggester,
            role=ContributorRole.SUGGESTER,
            full_edit=True,
        )

        with patch.object(HANDLERS.email, "send_project_approved_email") as mock_send:
            email_tasks.send_project_approved_email.call(str(project.id))

        recipients = {call.args[1].id for call in mock_send.call_args_list}
        assert recipients == {suggester.id}
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
