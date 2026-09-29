from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_length,
    is_,
    none,
)

from api.tasks import email as email_tasks
from apps.emails.models import SentEmail, SentEmailType
from apps.projects.models import (
    ContributorRole,
    ProjectContributor,
    ProjectReport,
    ProjectStatus,
)
from services import REPO
from services.project.django_impl.handler import PROJECT_REPORT_EMAIL_COOLDOWN
from tests.factories import ProjectFactory, UserFactory


def _report(client, project, **payload):
    body = {"reason": "site_down", **payload}
    return client.post(
        f"/api/projects/{project.slug or project.id}/reports",
        body,
        content_type="application/json",
    )


@pytest.mark.django_db
class TestReportProjectEndpoint:
    def test_anonymous_visitor_can_report(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")

        response = _report(client, project, details="  Blank page since Monday  ")

        assert_that(response.status_code, equal_to(201))
        report = ProjectReport.objects.get()
        assert_that(report.project_id, equal_to(project.id))
        assert_that(report.reason, equal_to("site_down"))
        assert_that(report.details, equal_to("Blank page since Monday"))
        assert_that(report.reporter, is_(none()))

    def test_records_the_signed_in_reporter(self, client, user, auth_headers):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")

        response = client.post(
            f"/api/projects/{project.slug}/reports",
            {"reason": "other"},
            content_type="application/json",
            **auth_headers,
        )

        assert_that(response.status_code, equal_to(201))
        assert_that(ProjectReport.objects.get().reporter_id, equal_to(user.id))

    def test_accepts_the_project_id(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED)

        response = client.post(
            f"/api/projects/{project.id}/reports",
            {"reason": "wrong_link"},
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(201))

    @pytest.mark.parametrize(
        "status", [ProjectStatus.PENDING, ProjectStatus.DRAFT, ProjectStatus.REJECTED]
    )
    def test_unpublished_project_is_not_found(self, client, status):
        project = ProjectFactory(status=status, slug="hidden")

        response = _report(client, project)

        assert_that(response.status_code, equal_to(404))
        assert_that(ProjectReport.objects.exists(), is_(False))
        assert_that(mail.outbox, has_length(0))

    def test_unknown_project_is_not_found(self, client):
        response = client.post(
            "/api/projects/no-such-project/reports",
            {"reason": "site_down"},
            content_type="application/json",
        )
        assert_that(response.status_code, equal_to(404))

    def test_rejects_unknown_reason(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")
        response = _report(client, project, reason="i_dont_like_it")
        assert_that(response.status_code, equal_to(422))

    def test_rejects_invalid_contact_email(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")
        response = _report(client, project, contact_email="not-an-email")
        assert_that(response.status_code, equal_to(422))

    def test_rejects_overlong_details(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")
        response = _report(client, project, details="x" * 2001)
        assert_that(response.status_code, equal_to(422))

    def test_rate_limited_per_ip(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")
        for _ in range(5):
            assert_that(_report(client, project).status_code, equal_to(201))

        response = _report(client, project)

        assert_that(response.status_code, equal_to(429))
        assert_that(ProjectReport.objects.count(), equal_to(5))


@pytest.mark.django_db
class TestProjectReportEmail:
    def test_emails_the_maker(self, client):
        maker = UserFactory(first_name="Jóna")
        project = ProjectFactory(
            status=ProjectStatus.APPROVED,
            slug="dead-app",
            creator=maker,
            title="Dead App",
            website_url="https://dead.example.is",
        )

        _report(client, project, reason="something_broken", details="Login 500s")

        assert_that(mail.outbox, has_length(1))
        message = mail.outbox[0]
        assert_that(message.to, equal_to([maker.email]))
        assert_that(message.subject, contains_string("Dead App"))
        assert_that(message.body, contains_string("Hi Jóna"))
        assert_that(message.body, contains_string("Something on the site is broken"))
        assert_that(message.body, contains_string("Login 500s"))
        assert_that(message.body, contains_string("https://dead.example.is"))
        assert_that(message.body, contains_string(f"/my-projects/{project.id}"))
        sent = SentEmail.objects.get()
        assert_that(sent.email_type, equal_to(SentEmailType.PROJECT_REPORT))
        assert_that(sent.project_id, equal_to(project.id))

    def test_plain_text_is_not_html_escaped(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")

        _report(client, project, details="It's <broken> & gone")

        assert_that(mail.outbox[0].body, contains_string("It's <broken> & gone"))

    def test_html_escapes_details(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")

        _report(client, project, details="<script>alert(1)</script>")

        html = mail.outbox[0].alternatives[0][0]
        assert_that(html, contains_string("&lt;script&gt;"))

    def test_reply_goes_to_the_reporter_when_they_left_an_address(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")

        _report(client, project, contact_email="visitor@example.com")

        message = mail.outbox[0]
        assert_that(message.reply_to, equal_to(["visitor@example.com"]))
        assert_that(message.body, contains_string("reply to this email"))

    def test_no_reply_to_without_an_address(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")

        _report(client, project)

        message = mail.outbox[0]
        assert_that(message.reply_to, equal_to([]))
        assert_that(message.body, contains_string("didn't leave a contact address"))

    def test_signed_in_reporter_address_is_not_shared_unless_given(
        self, client, auth_headers
    ):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")

        client.post(
            f"/api/projects/{project.slug}/reports",
            {"reason": "site_down"},
            content_type="application/json",
            **auth_headers,
        )

        assert_that(mail.outbox[0].reply_to, equal_to([]))

    def test_emails_every_full_edit_contributor(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")
        co_maker = UserFactory()
        ProjectContributor.objects.create(
            project=project, user=co_maker, role=ContributorRole.OWNER
        )
        viewer = UserFactory()
        ProjectContributor.objects.create(
            project=project,
            user=viewer,
            role=ContributorRole.TIPSTER,
            full_edit=False,
        )

        _report(client, project)

        recipients = sorted(m.to[0] for m in mail.outbox)
        assert_that(
            recipients, equal_to(sorted([project.creator.email, co_maker.email]))
        )

    def test_unclaimed_tipoff_goes_to_the_admin_address(self, client, settings):
        settings.NEW_PROJECT_NOTIFICATION_EMAIL = "admin@naglasupan.is"
        seed = REPO.users.get_community_user()
        project = ProjectFactory(
            status=ProjectStatus.APPROVED,
            slug="tipoff",
            creator=seed,
            is_community_tipoff=True,
        )

        _report(client, project)

        assert_that(mail.outbox, has_length(1))
        message = mail.outbox[0]
        assert_that(message.to, equal_to(["admin@naglasupan.is"]))
        assert_that(message.body, contains_string("no maker on Naglasúpan"))

    def test_unclaimed_tipoff_without_admin_address_sends_nothing(
        self, client, settings
    ):
        settings.NEW_PROJECT_NOTIFICATION_EMAIL = ""
        seed = REPO.users.get_community_user()
        project = ProjectFactory(
            status=ProjectStatus.APPROVED, slug="tipoff", creator=seed
        )

        response = _report(client, project)

        assert_that(response.status_code, equal_to(201))
        assert_that(mail.outbox, has_length(0))

    def test_one_failing_recipient_does_not_stop_the_others(self, client, monkeypatch):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")
        co_maker = UserFactory()
        ProjectContributor.objects.create(
            project=project, user=co_maker, role=ContributorRole.OWNER
        )
        report = ProjectReport.objects.create(project=project, reason="site_down")
        sent_to = []

        def flaky_send(report, recipient_email, recipient):
            sent_to.append(recipient_email)
            if recipient_email == project.creator.email:
                raise ConnectionError

        from services import HANDLERS  # noqa: PLC0415

        monkeypatch.setattr(HANDLERS.email, "send_project_report_email", flaky_send)

        email_tasks.send_project_report_email.call(str(report.id))

        assert_that(
            sorted(sent_to), equal_to(sorted([project.creator.email, co_maker.email]))
        )


@pytest.mark.django_db
class TestProjectReportEmailCooldown:
    def test_a_second_report_inside_the_cooldown_is_kept_but_not_emailed(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")

        _report(client, project, details="first")
        response = _report(client, project, details="second")

        assert_that(response.status_code, equal_to(201))
        assert_that(mail.outbox, has_length(1))
        assert_that(mail.outbox[0].body, contains_string("first"))
        second = ProjectReport.objects.get(details="second")
        assert_that(second.makers_notified, is_(False))

    def test_cooldown_is_per_project(self, client):
        one = ProjectFactory(status=ProjectStatus.APPROVED, slug="one")
        two = ProjectFactory(status=ProjectStatus.APPROVED, slug="two")

        _report(client, one)
        _report(client, two)

        assert_that(mail.outbox, has_length(2))

    def test_emails_again_once_the_cooldown_has_passed(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")
        _report(client, project)
        ProjectReport.objects.update(
            created_at=timezone.now()
            - PROJECT_REPORT_EMAIL_COOLDOWN
            - timedelta(minutes=1)
        )

        _report(client, project)

        assert_that(mail.outbox, has_length(2))
        assert_that(
            ProjectReport.objects.filter(makers_notified=True).count(), equal_to(2)
        )

    def test_an_unsent_report_does_not_restart_the_cooldown(self, client):
        project = ProjectFactory(status=ProjectStatus.APPROVED, slug="dead-app")
        ProjectReport.objects.create(
            project=project, reason="site_down", makers_notified=False
        )

        _report(client, project)

        assert_that(mail.outbox, has_length(1))
