import pytest

from services.email.django_impl import DjangoEmailQuery, render_email
from tests.factories import BroadcastEmailFactory, UserFactory

query = DjangoEmailQuery()


class TestRenderBroadcastEmail:
    def test_markdown_converts_to_html(self):
        broadcast = BroadcastEmailFactory.build(
            body_markdown="Hello **world**!",
        )

        html, _ = query.render_broadcast_email(broadcast)

        assert "<strong>world</strong>" in html

    def test_subject_present_in_html(self):
        broadcast = BroadcastEmailFactory.build(
            subject="Important Update",
        )

        html, _ = query.render_broadcast_email(broadcast)

        assert "Important Update" in html

    def test_unsubscribe_link_present_in_html(self):
        broadcast = BroadcastEmailFactory.build()

        html, _ = query.render_broadcast_email(broadcast)

        assert "/profile" in html
        assert "email preferences" in html.lower()

    def test_plain_text_contains_raw_markdown(self):
        broadcast = BroadcastEmailFactory.build(
            body_markdown="Hello **world**!",
        )

        _, text = query.render_broadcast_email(broadcast)

        assert "Hello **world**!" in text

    def test_plain_text_contains_subject(self):
        broadcast = BroadcastEmailFactory.build(
            subject="Big News",
        )

        _, text = query.render_broadcast_email(broadcast)

        assert "Big News" in text

    def test_plain_text_contains_unsubscribe_link(self):
        broadcast = BroadcastEmailFactory.build()

        _, text = query.render_broadcast_email(broadcast)

        assert "/profile" in text


@pytest.mark.django_db
class TestResolveBroadcastRecipients:
    def test_platform_updates_returns_opted_in_users(self):
        opted_in = UserFactory(email_opt_in_platform_updates=True)
        UserFactory(email_opt_in_platform_updates=False)

        broadcast = BroadcastEmailFactory(
            email_type="platform_updates",
            created_by=UserFactory(email_opt_in_platform_updates=False),
        )
        recipients = query.resolve_broadcast_recipients(broadcast)

        assert list(recipients) == [opted_in]

    def test_competition_results_returns_opted_in_users(self):
        opted_in = UserFactory(email_opt_in_competition_results=True)
        UserFactory(email_opt_in_competition_results=False)

        broadcast = BroadcastEmailFactory(
            email_type="competition_results",
            created_by=UserFactory(email_opt_in_competition_results=False),
        )
        recipients = query.resolve_broadcast_recipients(broadcast)

        assert list(recipients) == [opted_in]

    def test_no_type_returns_individual_recipients(self):
        user1 = UserFactory()
        user2 = UserFactory()
        UserFactory()

        broadcast = BroadcastEmailFactory(
            email_type=None,
            individual_recipients=[user1, user2],
        )
        recipients = query.resolve_broadcast_recipients(broadcast)

        assert set(recipients) == {user1, user2}

    def test_inactive_users_excluded_from_platform_updates(self):
        UserFactory(
            email_opt_in_platform_updates=True,
            is_active=False,
        )

        broadcast = BroadcastEmailFactory(
            email_type="platform_updates",
            created_by=UserFactory(email_opt_in_platform_updates=False),
        )
        recipients = query.resolve_broadcast_recipients(broadcast)

        assert recipients.count() == 0

    def test_inactive_users_excluded_from_competition_results(self):
        UserFactory(
            email_opt_in_competition_results=True,
            is_active=False,
        )

        broadcast = BroadcastEmailFactory(
            email_type="competition_results",
            created_by=UserFactory(email_opt_in_competition_results=False),
        )
        recipients = query.resolve_broadcast_recipients(broadcast)

        assert recipients.count() == 0

    def test_inactive_users_excluded_from_individual_recipients(self):
        inactive = UserFactory(is_active=False)

        broadcast = BroadcastEmailFactory(
            email_type=None,
            individual_recipients=[inactive],
        )
        recipients = query.resolve_broadcast_recipients(broadcast)

        assert recipients.count() == 0


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
