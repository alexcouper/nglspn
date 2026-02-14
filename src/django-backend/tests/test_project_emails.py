from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from api.services.email import render_email, send_project_approved_email
from apps.projects.admin import ProjectAdmin
from apps.projects.models import Project, ProjectStatus

from .factories import ProjectFactory, UserFactory


class TestRenderProjectApprovedEmail:
    def test_renders_html_with_project_title(self):
        html, _ = render_email(
            "project_approved",
            {
                "user_name": "Test",
                "project_title": "My Cool Project",
                "project_url": "https://naglasupan.is/projects/123",
                "logo_url": "https://example.com/logo.png",
                "current_year": 2026,
            },
        )

        assert "My Cool Project" in html
        assert "#6366f1" in html

    def test_renders_html_with_project_url(self):
        html, _ = render_email(
            "project_approved",
            {
                "user_name": "Test",
                "project_title": "My Cool Project",
                "project_url": "https://naglasupan.is/projects/abc-123",
                "logo_url": "https://example.com/logo.png",
                "current_year": 2026,
            },
        )

        assert "https://naglasupan.is/projects/abc-123" in html

    def test_renders_plain_text_with_project_title_and_url(self):
        _, text = render_email(
            "project_approved",
            {
                "user_name": "Alice",
                "project_title": "My Cool Project",
                "project_url": "https://naglasupan.is/projects/123",
                "logo_url": "https://example.com/logo.png",
                "current_year": 2026,
            },
        )

        assert "My Cool Project" in text
        assert "https://naglasupan.is/projects/123" in text
        assert "Hi Alice" in text


@pytest.mark.django_db
class TestSendProjectApprovedEmail:
    def test_sends_email_with_html_and_text_parts(self, mailoutbox):
        project = ProjectFactory(title="Awesome App")

        send_project_approved_email(project)

        assert len(mailoutbox) == 1
        email = mailoutbox[0]
        assert email.to == [project.owner.email]
        assert email.subject == "Your project has been approved - Naglasúpan"
        assert "Awesome App" in email.body
        assert len(email.alternatives) == 1
        html_content, mime_type = email.alternatives[0]
        assert mime_type == "text/html"
        assert "Awesome App" in html_content


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

        with patch("apps.projects.admin.send_project_approved_email") as mock_send:
            self._call_action(projects)

        assert mock_send.call_count == 2

    def test_does_not_send_email_for_non_pending_projects(self):
        approved_project = ProjectFactory(status=ProjectStatus.APPROVED)

        with patch("apps.projects.admin.send_project_approved_email") as mock_send:
            self._call_action([approved_project])

        mock_send.assert_not_called()

    def test_continues_approval_on_email_failure(self):
        projects = ProjectFactory.create_batch(2)

        with patch(
            "apps.projects.admin.send_project_approved_email",
            side_effect=Exception("SMTP error"),
        ):
            self._call_action(projects)

        for project in projects:
            project.refresh_from_db()
            assert project.status == ProjectStatus.APPROVED
