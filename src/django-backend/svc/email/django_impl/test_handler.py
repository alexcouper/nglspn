from unittest.mock import patch

import pytest

from apps.emails.models import BroadcastEmailRecipient
from svc.email.django_impl import DjangoEmailHandler
from tests.factories import BroadcastEmailFactory, ProjectFactory, UserFactory

handler = DjangoEmailHandler()


@pytest.mark.django_db
class TestSendVerificationEmail:
    def test_sends_email_with_code(self, mailoutbox):
        user = UserFactory(first_name="Alice")

        handler.send_verification_email(user, "987654", expires_minutes=15)

        assert len(mailoutbox) == 1
        email = mailoutbox[0]
        assert email.to == [user.email]
        assert "Verify your email" in email.subject
        assert "987654" in email.body

    def test_sends_email_with_html_and_text_parts(self, mailoutbox):
        user = UserFactory(first_name="Bob")

        handler.send_verification_email(user, "654321", expires_minutes=15)

        assert len(mailoutbox) == 1
        email = mailoutbox[0]
        assert email.to == [user.email]
        assert email.subject == "Verify your email - Naglasúpan"
        assert "654321" in email.body  # plain text body
        assert len(email.alternatives) == 1
        html_content, mime_type = email.alternatives[0]
        assert mime_type == "text/html"
        assert "654321" in html_content
        assert "#ffffff" in html_content  # white background


@pytest.mark.django_db
class TestSendProjectApprovedEmail:
    def test_sends_email_with_html_and_text_parts(self, mailoutbox):
        project = ProjectFactory(title="Awesome App")

        handler.send_project_approved_email(project)

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
class TestSendBroadcast:
    def _make_broadcast_with_recipients(self, count=2, **kwargs):
        admin = UserFactory(
            is_staff=True,
            is_superuser=True,
            email_opt_in_platform_updates=False,
        )
        users = [UserFactory(email_opt_in_platform_updates=True) for _ in range(count)]
        broadcast = BroadcastEmailFactory(
            email_type="platform_updates",
            created_by=admin,
            **kwargs,
        )
        return broadcast, admin, users

    def test_sends_to_all_resolved_recipients(self, mailoutbox):
        broadcast, admin, users = self._make_broadcast_with_recipients(2)
        handler.send_broadcast(broadcast, admin)

        assert len(mailoutbox) == 2
        sent_to = {m.to[0] for m in mailoutbox}
        assert sent_to == {u.email for u in users}

    def test_sets_sent_at_and_sent_by(self):
        broadcast, admin, _ = self._make_broadcast_with_recipients(1)
        handler.send_broadcast(broadcast, admin)

        broadcast.refresh_from_db()
        assert broadcast.sent_at is not None
        assert broadcast.sent_by == admin

    def test_creates_delivery_records(self):
        broadcast, admin, users = self._make_broadcast_with_recipients(1)
        handler.send_broadcast(broadcast, admin)

        records = BroadcastEmailRecipient.objects.filter(broadcast_email=broadcast)
        assert records.count() == 1
        record = records.first()
        assert record.user == users[0]
        assert record.success is True
        assert record.error_message == ""

    def test_continues_on_individual_failure(self):
        broadcast, admin, _ = self._make_broadcast_with_recipients(2)
        call_count = 0

        with patch(
            "svc.email.django_impl.handler.EmailMultiAlternatives.send",
        ) as mock_send:

            def fail_first(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    msg = "SMTP error"
                    raise Exception(msg)  # noqa: TRY002

            mock_send.side_effect = fail_first
            success_count, failure_count = handler.send_broadcast(broadcast, admin)

        assert success_count == 1
        assert failure_count == 1

    def test_records_error_messages(self):
        broadcast, admin, _ = self._make_broadcast_with_recipients(1)

        with patch(
            "svc.email.django_impl.handler.EmailMultiAlternatives.send",
            side_effect=Exception("SMTP error"),
        ):
            handler.send_broadcast(broadcast, admin)

        record = BroadcastEmailRecipient.objects.get(broadcast_email=broadcast)
        assert record.success is False
        assert record.error_message != ""

    def test_returns_correct_counts(self, mailoutbox):
        broadcast, admin, _ = self._make_broadcast_with_recipients(2)
        success_count, failure_count = handler.send_broadcast(broadcast, admin)

        assert success_count == 2
        assert failure_count == 0

    def test_email_has_html_and_text_parts(self, mailoutbox):
        broadcast, admin, _ = self._make_broadcast_with_recipients(
            1,
            body_markdown="Hello **world**!",
        )
        handler.send_broadcast(broadcast, admin)

        email = mailoutbox[0]
        assert "Hello **world**!" in email.body
        assert len(email.alternatives) == 1
        html, mime = email.alternatives[0]
        assert mime == "text/html"
        assert "<strong>world</strong>" in html

    def test_email_subject_includes_naglasupan(self, mailoutbox):
        broadcast, admin, _ = self._make_broadcast_with_recipients(
            1,
            subject="Big News",
        )
        handler.send_broadcast(broadcast, admin)

        assert mailoutbox[0].subject == "Big News - Naglasúpan"
