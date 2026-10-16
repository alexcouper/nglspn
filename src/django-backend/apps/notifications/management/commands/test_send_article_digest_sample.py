from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.emails.models import SentEmail
from apps.notifications.models import Notification
from tests.factories import ProjectFactory, PublishedArticleFactory


def send_sample(*args: str) -> str:
    buffer = StringIO()
    call_command(
        "send_article_digest_sample", "--to", "qa@example.com", *args, stdout=buffer
    )
    return buffer.getvalue()


def subjects_of(mailoutbox) -> list[str]:
    return [m.subject for m in mailoutbox]


@pytest.mark.django_db
class TestSendArticleDigestSample:
    def test_sends_one_email_per_layout(self, mailoutbox):
        PublishedArticleFactory(title="Only one", project=ProjectFactory(title="P"))

        send_sample()

        assert subjects_of(mailoutbox) == [
            "[digest sample: single] P: Only one",
            "[digest sample: lead] P: Only one, and 0 more",
            "[digest sample: list] 1 new articles - Naglasúpan",
        ]
        assert all(m.to == ["qa@example.com"] for m in mailoutbox)

    def test_one_layout_only(self, mailoutbox):
        PublishedArticleFactory()

        send_sample("--layout", "single")

        assert len(mailoutbox) == 1
        assert mailoutbox[0].subject.startswith("[digest sample: single]")

    def test_chosen_article_leads(self, mailoutbox):
        PublishedArticleFactory(title="Newest")
        PublishedArticleFactory(title="Chosen", slug="chosen")

        send_sample("--layout", "single", "--article", "chosen")

        assert mailoutbox[0].subject.endswith("Chosen")

    def test_leaves_no_rows_behind(self, mailoutbox):
        PublishedArticleFactory()

        send_sample()

        assert Notification.objects.count() == 0
        assert SentEmail.objects.count() == 0

    def test_fails_without_published_articles(self):
        with pytest.raises(CommandError, match="No published articles"):
            send_sample()

    def test_fails_on_an_unknown_article(self):
        PublishedArticleFactory()

        with pytest.raises(CommandError, match="No published article with slug"):
            send_sample("--article", "nope")
