import pytest

from svc.email.django_impl import DjangoEmailQuery
from tests.factories import BroadcastEmailFactory, UserFactory

query = DjangoEmailQuery()


@pytest.mark.django_db
class TestRenderBroadcastEmail:
    def test_returns_html_and_text(self):
        broadcast = BroadcastEmailFactory(
            subject="Test Subject",
            body_markdown="Hello **world**!",
        )

        html, text = query.render_broadcast_email(broadcast)

        assert "<strong>world</strong>" in html
        assert "Hello" in text


@pytest.mark.django_db
class TestResolveBroadcastRecipients:
    def test_returns_opted_in_users_for_platform_updates(self):
        opted_in = UserFactory(email_opt_in_platform_updates=True)
        opted_out = UserFactory(email_opt_in_platform_updates=False)
        broadcast = BroadcastEmailFactory(email_type="platform_updates")

        recipients = list(query.resolve_broadcast_recipients(broadcast))

        assert opted_in in recipients
        assert opted_out not in recipients

    def test_returns_individual_recipients_for_null_type(self):
        user = UserFactory()
        broadcast = BroadcastEmailFactory(
            email_type=None,
            individual_recipients=[user],
        )

        recipients = query.resolve_broadcast_recipients(broadcast)

        assert list(recipients) == [user]
