from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from api.services.email import (
    render_broadcast_email,
    resolve_broadcast_recipients,
    send_broadcast,
)
from apps.emails.admin import BroadcastEmailAdmin, BroadcastEmailImageInline
from apps.emails.models import (
    BroadcastEmail,
    BroadcastEmailImage,
    BroadcastEmailRecipient,
)

from .factories import BroadcastEmailFactory, BroadcastEmailImageFactory, UserFactory


class TestRenderBroadcastEmail:
    def test_markdown_converts_to_html(self):
        broadcast = BroadcastEmailFactory.build(
            body_markdown="Hello **world**!",
        )

        html, _ = render_broadcast_email(broadcast)

        assert "<strong>world</strong>" in html

    def test_subject_present_in_html(self):
        broadcast = BroadcastEmailFactory.build(
            subject="Important Update",
        )

        html, _ = render_broadcast_email(broadcast)

        assert "Important Update" in html

    def test_unsubscribe_link_present_in_html(self):
        broadcast = BroadcastEmailFactory.build()

        html, _ = render_broadcast_email(broadcast)

        assert "/profile" in html
        assert "email preferences" in html.lower()

    def test_plain_text_contains_raw_markdown(self):
        broadcast = BroadcastEmailFactory.build(
            body_markdown="Hello **world**!",
        )

        _, text = render_broadcast_email(broadcast)

        assert "Hello **world**!" in text

    def test_plain_text_contains_subject(self):
        broadcast = BroadcastEmailFactory.build(
            subject="Big News",
        )

        _, text = render_broadcast_email(broadcast)

        assert "Big News" in text

    def test_plain_text_contains_unsubscribe_link(self):
        broadcast = BroadcastEmailFactory.build()

        _, text = render_broadcast_email(broadcast)

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
        recipients = resolve_broadcast_recipients(broadcast)

        assert list(recipients) == [opted_in]

    def test_competition_results_returns_opted_in_users(self):
        opted_in = UserFactory(email_opt_in_competition_results=True)
        UserFactory(email_opt_in_competition_results=False)

        broadcast = BroadcastEmailFactory(
            email_type="competition_results",
            created_by=UserFactory(email_opt_in_competition_results=False),
        )
        recipients = resolve_broadcast_recipients(broadcast)

        assert list(recipients) == [opted_in]

    def test_no_type_returns_individual_recipients(self):
        user1 = UserFactory()
        user2 = UserFactory()
        UserFactory()

        broadcast = BroadcastEmailFactory(
            email_type=None,
            individual_recipients=[user1, user2],
        )
        recipients = resolve_broadcast_recipients(broadcast)

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
        recipients = resolve_broadcast_recipients(broadcast)

        # Only the factory-created admin user (who has opt-in True by default)
        # should remain - but we set it to False, so count is 0
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
        recipients = resolve_broadcast_recipients(broadcast)

        assert recipients.count() == 0

    def test_inactive_users_excluded_from_individual_recipients(self):
        inactive = UserFactory(is_active=False)

        broadcast = BroadcastEmailFactory(
            email_type=None,
            individual_recipients=[inactive],
        )
        recipients = resolve_broadcast_recipients(broadcast)

        assert recipients.count() == 0


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
        send_broadcast(broadcast, admin)

        assert len(mailoutbox) == 2
        sent_to = {m.to[0] for m in mailoutbox}
        assert sent_to == {u.email for u in users}

    def test_sets_sent_at_and_sent_by(self):
        broadcast, admin, _ = self._make_broadcast_with_recipients(1)
        send_broadcast(broadcast, admin)

        broadcast.refresh_from_db()
        assert broadcast.sent_at is not None
        assert broadcast.sent_by == admin

    def test_creates_delivery_records(self):
        broadcast, admin, users = self._make_broadcast_with_recipients(1)
        send_broadcast(broadcast, admin)

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
            "api.services.email.EmailMultiAlternatives.send",
        ) as mock_send:

            def fail_first(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    msg = "SMTP error"
                    raise Exception(msg)  # noqa: TRY002

            mock_send.side_effect = fail_first
            success_count, failure_count = send_broadcast(broadcast, admin)

        assert success_count == 1
        assert failure_count == 1

    def test_records_error_messages(self):
        broadcast, admin, _ = self._make_broadcast_with_recipients(1)

        with patch(
            "api.services.email.EmailMultiAlternatives.send",
            side_effect=Exception("SMTP error"),
        ):
            send_broadcast(broadcast, admin)

        record = BroadcastEmailRecipient.objects.get(broadcast_email=broadcast)
        assert record.success is False
        assert record.error_message != ""

    def test_returns_correct_counts(self, mailoutbox):
        broadcast, admin, _ = self._make_broadcast_with_recipients(2)
        success_count, failure_count = send_broadcast(broadcast, admin)

        assert success_count == 2
        assert failure_count == 0

    def test_email_has_html_and_text_parts(self, mailoutbox):
        broadcast, admin, _ = self._make_broadcast_with_recipients(
            1,
            body_markdown="Hello **world**!",
        )
        send_broadcast(broadcast, admin)

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
        send_broadcast(broadcast, admin)

        assert mailoutbox[0].subject == "Big News - Naglasúpan"


@pytest.mark.django_db
class TestBroadcastEmailAdmin:
    def _get_admin(self):
        site = AdminSite()
        return BroadcastEmailAdmin(BroadcastEmail, site)

    def _make_request(self, path="/admin/", user=None):
        factory = RequestFactory()
        request = factory.get(path)
        request.user = user or UserFactory(is_staff=True, is_superuser=True)
        request.session = "session"
        request._messages = FallbackStorage(request)  # noqa: SLF001
        return request

    def test_save_model_sets_created_by(self):
        admin_obj = self._get_admin()
        user = UserFactory(is_staff=True, is_superuser=True)
        request = self._make_request(user=user)

        broadcast = BroadcastEmail(subject="Test", body_markdown="Body")
        admin_obj.save_model(request, broadcast, form=None, change=False)

        assert broadcast.created_by == user

    def test_sent_emails_are_readonly(self):
        admin_obj = self._get_admin()
        broadcast = BroadcastEmailFactory()
        broadcast.sent_at = "2026-01-01T00:00:00Z"

        request = self._make_request()
        readonly = admin_obj.get_readonly_fields(request, broadcast)

        assert "subject" in readonly
        assert "body_markdown" in readonly
        assert "email_type" in readonly

    def test_draft_emails_are_editable(self):
        admin_obj = self._get_admin()
        broadcast = BroadcastEmailFactory()

        request = self._make_request()
        readonly = admin_obj.get_readonly_fields(request, broadcast)

        assert "subject" not in readonly
        assert "body_markdown" not in readonly

    def test_cannot_delete_sent_email(self):
        admin_obj = self._get_admin()
        broadcast = BroadcastEmailFactory()
        broadcast.sent_at = "2026-01-01T00:00:00Z"

        request = self._make_request()
        assert admin_obj.has_delete_permission(request, broadcast) is False

    def test_can_delete_draft_email(self):
        admin_obj = self._get_admin()
        broadcast = BroadcastEmailFactory()

        request = self._make_request()
        assert admin_obj.has_delete_permission(request, broadcast) is True


@pytest.mark.django_db
class TestBroadcastEmailAdminViews:
    def test_preview_returns_html(self, admin_client):
        broadcast = BroadcastEmailFactory(
            body_markdown="Hello **preview**!",
        )

        url = reverse(
            "admin:emails_broadcastemail_preview",
            args=[broadcast.pk],
        )
        response = admin_client.get(url)

        assert response.status_code == 200
        assert b"<strong>preview</strong>" in response.content

    def test_preview_text_format(self, admin_client):
        broadcast = BroadcastEmailFactory(
            body_markdown="Hello **preview**!",
        )

        url = reverse(
            "admin:emails_broadcastemail_preview",
            args=[broadcast.pk],
        )
        response = admin_client.get(url, {"format": "text"})

        assert response.status_code == 200
        assert b"Hello **preview**!" in response.content

    def test_send_view_shows_confirmation(self, admin_client):
        UserFactory(email_opt_in_platform_updates=True)
        broadcast = BroadcastEmailFactory(
            email_type="platform_updates",
            created_by=UserFactory(email_opt_in_platform_updates=False),
        )

        url = reverse(
            "admin:emails_broadcastemail_send",
            args=[broadcast.pk],
        )
        response = admin_client.get(url)

        assert response.status_code == 200
        assert b"Confirm" in response.content

    def test_send_view_post_sends_and_redirects(self, admin_client, mailoutbox):
        UserFactory(email_opt_in_platform_updates=True)
        broadcast = BroadcastEmailFactory(
            email_type="platform_updates",
            created_by=UserFactory(email_opt_in_platform_updates=False),
        )

        url = reverse(
            "admin:emails_broadcastemail_send",
            args=[broadcast.pk],
        )
        response = admin_client.post(url)

        assert response.status_code == 302
        broadcast.refresh_from_db()
        assert broadcast.sent_at is not None
        # admin_client creation may add emails to mailbox
        broadcast_emails = [m for m in mailoutbox if broadcast.subject in m.subject]
        assert len(broadcast_emails) >= 1

    def test_send_view_rejects_already_sent(self, admin_client):
        broadcast = BroadcastEmailFactory(email_type="platform_updates")
        broadcast.sent_at = timezone.now()
        broadcast.save()

        url = reverse(
            "admin:emails_broadcastemail_send",
            args=[broadcast.pk],
        )
        response = admin_client.post(url)

        assert response.status_code == 302

    def test_send_view_rejects_no_recipients(self, admin_client):
        broadcast = BroadcastEmailFactory(email_type=None)

        url = reverse(
            "admin:emails_broadcastemail_send",
            args=[broadcast.pk],
        )
        response = admin_client.get(url)

        assert response.status_code == 302


@pytest.mark.django_db
class TestBroadcastEmailImage:
    def test_auto_populates_original_filename(self):
        broadcast = BroadcastEmailFactory()
        image = BroadcastEmailImage(broadcast_email=broadcast)
        image.image.name = "my-photo.png"
        image.save()

        assert image.original_filename == "my-photo.png"

    def test_does_not_overwrite_explicit_original_filename(self):
        image = BroadcastEmailImageFactory(original_filename="custom-name.jpg")

        assert image.original_filename == "custom-name.jpg"

    def test_url_property_returns_image_url(self):
        image = BroadcastEmailImageFactory()

        assert image.url == image.image.url

    def test_str_returns_original_filename(self):
        image = BroadcastEmailImageFactory(original_filename="banner.png")

        assert str(image) == "banner.png"

    def test_cascade_deletes_with_broadcast(self):
        image = BroadcastEmailImageFactory()
        broadcast_pk = image.broadcast_email.pk
        BroadcastEmail.objects.get(pk=broadcast_pk).delete()

        assert BroadcastEmailImage.objects.count() == 0


@pytest.mark.django_db
class TestBroadcastEmailImageInline:
    def _get_admin(self):
        site = AdminSite()
        return BroadcastEmailAdmin(BroadcastEmail, site)

    def _make_request(self, user=None):
        factory = RequestFactory()
        request = factory.get("/admin/")
        request.user = user or UserFactory(is_staff=True, is_superuser=True)
        return request

    def test_draft_email_has_image_inline(self):
        admin_obj = self._get_admin()
        broadcast = BroadcastEmailFactory()
        request = self._make_request()

        inlines = admin_obj.get_inlines(request, broadcast)

        assert BroadcastEmailImageInline in inlines

    def test_sent_email_has_no_image_inline(self):
        admin_obj = self._get_admin()
        broadcast = BroadcastEmailFactory()
        broadcast.sent_at = timezone.now()

        request = self._make_request()
        inlines = admin_obj.get_inlines(request, broadcast)

        assert BroadcastEmailImageInline not in inlines

    def test_new_email_has_no_image_inline(self):
        admin_obj = self._get_admin()
        request = self._make_request()

        inlines = admin_obj.get_inlines(request, obj=None)

        assert inlines == []

    def test_thumbnail_preview_shows_insert_button(self):
        image = BroadcastEmailImageFactory(original_filename="photo.png")

        inline = BroadcastEmailImageInline(BroadcastEmailImage, AdminSite())
        html = inline.thumbnail_preview(image)

        assert "broadcast-image-insert" in html
        assert "photo.png" in html

    def test_thumbnail_preview_unsaved_shows_message(self):
        image = BroadcastEmailImage()

        inline = BroadcastEmailImageInline(BroadcastEmailImage, AdminSite())
        result = inline.thumbnail_preview(image)

        assert result == "Save to see preview"
