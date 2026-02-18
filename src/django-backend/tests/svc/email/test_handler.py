import pytest

from svc.email.django_impl import DjangoEmailHandler
from tests.factories import ProjectFactory, UserFactory

handler = DjangoEmailHandler()


@pytest.mark.django_db
class TestSendVerificationEmail:
    def test_sends_email_with_code(self, mailoutbox):
        user = UserFactory(first_name="Alice")

        handler.send_verification_email(user, "987654")

        assert len(mailoutbox) == 1
        email = mailoutbox[0]
        assert email.to == [user.email]
        assert "Verify your email" in email.subject
        assert "987654" in email.body


@pytest.mark.django_db
class TestSendProjectApprovedEmail:
    def test_sends_email_to_project_owner(self, mailoutbox):
        project = ProjectFactory(title="My App")

        handler.send_project_approved_email(project)

        assert len(mailoutbox) == 1
        email = mailoutbox[0]
        assert email.to == [project.owner.email]
        assert "approved" in email.subject.lower()
        assert "My App" in email.body
