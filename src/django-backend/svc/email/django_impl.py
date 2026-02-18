from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import markdown
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from mjml import mjml_to_html

from apps.emails.models import BroadcastEmailRecipient
from svc.users.django_impl import VERIFICATION_CODE_EXPIRY_MINUTES, DjangoUserQuery

from .handler_interface import EmailHandlerInterface
from .query_interface import EmailQueryInterface

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from apps.emails.models import BroadcastEmail
    from apps.projects.models import Project
    from apps.users.models import User

logger = logging.getLogger(__name__)


def render_email(template_name: str, context: dict) -> tuple[str, str]:
    mjml_content = render_to_string(f"email/{template_name}.mjml", context)
    result = mjml_to_html(mjml_content)
    html = result.html
    text = render_to_string(f"email/{template_name}.txt", context)
    return html, text


class DjangoEmailQuery(EmailQueryInterface):
    def render_broadcast_email(self, broadcast: BroadcastEmail) -> tuple[str, str]:
        body_html = markdown.markdown(
            broadcast.body_markdown,
            extensions=["extra", "smarty"],
        )
        context = {
            "subject": broadcast.subject,
            "body_html": body_html,
            "body_markdown": broadcast.body_markdown,
            "profile_url": f"{settings.FRONTEND_URL}/profile",
            "logo_url": f"{settings.S3_PUBLIC_URL_BASE}/email/logo.png",
            "current_year": timezone.now().year,
        }
        return render_email("broadcast", context)

    def resolve_broadcast_recipients(self, broadcast: BroadcastEmail) -> QuerySet:
        if broadcast.email_type in ("platform_updates", "competition_results"):
            return DjangoUserQuery().list_opted_in_for_broadcast_type(
                broadcast.email_type
            )
        return broadcast.individual_recipients.filter(is_active=True)


class DjangoEmailHandler(EmailHandlerInterface):
    def send_verification_email(self, user: User, code: str) -> None:
        context = {
            "code": code,
            "expiry_minutes": VERIFICATION_CODE_EXPIRY_MINUTES,
            "user_name": user.first_name or "there",
            "logo_url": f"{settings.S3_PUBLIC_URL_BASE}/email/logo.png",
            "current_year": timezone.now().year,
        }
        html, text = render_email("verification_code", context)

        email = EmailMultiAlternatives(
            subject="Verify your email - Naglasúpan",
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html, "text/html")
        email.send(fail_silently=False)

    def send_project_approved_email(self, project: Project) -> None:
        owner = project.owner
        context = {
            "user_name": owner.first_name or "there",
            "project_title": project.title,
            "project_url": f"{settings.FRONTEND_URL}/projects/{project.id}",
            "logo_url": f"{settings.S3_PUBLIC_URL_BASE}/email/logo.png",
            "current_year": timezone.now().year,
        }
        html, text = render_email("project_approved", context)

        email = EmailMultiAlternatives(
            subject="Your project has been approved - Naglasúpan",
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[owner.email],
        )
        email.attach_alternative(html, "text/html")
        email.send(fail_silently=False)

    def send_broadcast(
        self,
        broadcast: BroadcastEmail,
        sent_by_user: User,
    ) -> tuple[int, int]:
        query = DjangoEmailQuery()
        html, text = query.render_broadcast_email(broadcast)
        recipients = query.resolve_broadcast_recipients(broadcast)
        success_count = 0
        failure_count = 0

        for user in recipients.iterator():
            error_message = ""
            success = True
            try:
                email = EmailMultiAlternatives(
                    subject=f"{broadcast.subject} - Naglasúpan",
                    body=text,
                    from_email=settings.ADMIN_FROM_EMAIL,
                    to=[user.email],
                )
                email.attach_alternative(html, "text/html")
                email.send(fail_silently=False)
            except Exception:
                logger.exception("Failed to send broadcast email to %s", user.email)
                success = False
                failure_count += 1
                error_message = f"Failed to send to {user.email}"
            else:
                success_count += 1

            BroadcastEmailRecipient.objects.create(
                broadcast_email=broadcast,
                user=user,
                success=success,
                error_message=error_message,
            )

        broadcast.sent_at = timezone.now()
        broadcast.sent_by = sent_by_user
        broadcast.save(update_fields=["sent_at", "sent_by"])

        return success_count, failure_count
