from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from apps.projects.admin import ProjectAdmin
from apps.projects.models import Project, ProjectStatus
from svc import HANDLERS

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
