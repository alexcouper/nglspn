from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from apps.emails.models import BroadcastEmailRecipient
from services.email import EMAIL_LOGO_URL
from services.email.handler_interface import EmailHandlerInterface

from . import render_email
from .query import DjangoEmailQuery

if TYPE_CHECKING:
    from apps.emails.models import BroadcastEmail
    from apps.projects.models import Project
    from apps.users.models import User

logger = logging.getLogger(__name__)


class DjangoEmailHandler(EmailHandlerInterface):
    def send_verification_email(
        self,
        user: User,
        code: str,
        expires_minutes: int,
    ) -> None:
        context = {
            "code": code,
            "expiry_minutes": expires_minutes,
            "user_name": user.first_name or "there",
            "logo_url": EMAIL_LOGO_URL,
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

    def send_password_reset_email(
        self,
        user: User,
        code: str,
        expires_minutes: int,
    ) -> None:
        context = {
            "code": code,
            "expiry_minutes": expires_minutes,
            "user_name": user.first_name or "there",
            "logo_url": EMAIL_LOGO_URL,
            "current_year": timezone.now().year,
        }
        html, text = render_email("password_reset_code", context)

        email = EmailMultiAlternatives(
            subject="Reset your password - Naglasúpan",
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
            "logo_url": EMAIL_LOGO_URL,
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
