from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from apps.emails.models import BroadcastEmailRecipient, SentEmail, SentEmailType
from services.email import EMAIL_LOGO_URL
from services.email.handler_interface import EmailHandlerInterface

from . import render_email
from .query import DjangoEmailQuery

if TYPE_CHECKING:
    from collections.abc import Sequence

    from apps.discussions.models import Discussion
    from apps.emails.models import BroadcastEmail
    from apps.notifications.models import Notification
    from apps.projects.models import Project
    from apps.users.models import User

logger = logging.getLogger(__name__)


def _log_sent_email(
    *,
    recipient: User | None,
    email_type: str,
    subject: str,
    to_email: str,
    success: bool = True,
    error_message: str = "",
) -> None:
    try:
        SentEmail.objects.create(
            recipient=recipient,
            email_type=email_type,
            subject=subject,
            to_email=to_email,
            success=success,
            error_message=error_message,
        )
    except Exception:
        logger.exception("Failed to log sent email record for %s", to_email)


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

        subject = "Verify your email - Naglasúpan"
        email = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html, "text/html")
        try:
            email.send(fail_silently=False)
        except Exception:
            _log_sent_email(
                recipient=user,
                email_type=SentEmailType.VERIFICATION,
                subject=subject,
                to_email=user.email,
                success=False,
                error_message=f"Failed to send to {user.email}",
            )
            raise
        _log_sent_email(
            recipient=user,
            email_type=SentEmailType.VERIFICATION,
            subject=subject,
            to_email=user.email,
        )

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

        subject = "Reset your password - Naglasúpan"
        email = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html, "text/html")
        try:
            email.send(fail_silently=False)
        except Exception:
            _log_sent_email(
                recipient=user,
                email_type=SentEmailType.PASSWORD_RESET,
                subject=subject,
                to_email=user.email,
                success=False,
                error_message=f"Failed to send to {user.email}",
            )
            raise
        _log_sent_email(
            recipient=user,
            email_type=SentEmailType.PASSWORD_RESET,
            subject=subject,
            to_email=user.email,
        )

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

        subject = "Your project has been approved - Naglasúpan"
        email = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[owner.email],
        )
        email.attach_alternative(html, "text/html")
        try:
            email.send(fail_silently=False)
        except Exception:
            _log_sent_email(
                recipient=owner,
                email_type=SentEmailType.PROJECT_APPROVED,
                subject=subject,
                to_email=owner.email,
                success=False,
                error_message=f"Failed to send to {owner.email}",
            )
            raise
        _log_sent_email(
            recipient=owner,
            email_type=SentEmailType.PROJECT_APPROVED,
            subject=subject,
            to_email=owner.email,
        )

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

    def send_discussion_notification_email(
        self, notification: Notification, discussion: Discussion
    ) -> None:
        author_name = "Someone"
        if discussion.author:
            author_name = discussion.author.full_name or discussion.author.email

        recipient = notification.recipient
        context = {
            "recipient_name": recipient.first_name or "there",
            "author_name": author_name,
            "project_title": discussion.project.title,
            "comment_body": discussion.body[:500],
            "discussion_url": (
                f"{settings.FRONTEND_URL}/projects/{discussion.project_id}/discussions"
            ),
            "logo_url": f"{settings.S3_PUBLIC_URL_BASE}/email/logo.png",
            "current_year": timezone.now().year,
        }
        html, text = render_email("discussion_notification", context)

        subject = f"New comment on {discussion.project.title} - Naglasúpan"
        email = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient.email],
        )
        email.attach_alternative(html, "text/html")
        try:
            email.send(fail_silently=False)
        except Exception:
            _log_sent_email(
                recipient=recipient,
                email_type=SentEmailType.DISCUSSION_NOTIFICATION,
                subject=subject,
                to_email=recipient.email,
                success=False,
                error_message=f"Failed to send to {recipient.email}",
            )
            raise
        _log_sent_email(
            recipient=recipient,
            email_type=SentEmailType.DISCUSSION_NOTIFICATION,
            subject=subject,
            to_email=recipient.email,
        )

    def send_discussion_digest_email(
        self, notifications: Sequence[Notification]
    ) -> None:
        if not notifications:
            return

        recipient = notifications[0].recipient
        groups_dict: dict[str, dict] = {}
        for n in notifications:
            project_title = n.discussion.project.title
            if project_title not in groups_dict:
                groups_dict[project_title] = {
                    "project_title": project_title,
                    "comments": [],
                }
            author_name = "Someone"
            if n.discussion.author:
                author_name = n.discussion.author.full_name or n.discussion.author.email
            groups_dict[project_title]["comments"].append(
                {"author_name": author_name, "body": n.discussion.body[:500]}
            )

        context = {
            "recipient_name": recipient.first_name or "there",
            "groups": list(groups_dict.values()),
            "site_url": settings.FRONTEND_URL,
            "logo_url": f"{settings.S3_PUBLIC_URL_BASE}/email/logo.png",
            "current_year": timezone.now().year,
        }
        html, text = render_email("discussion_digest", context)

        subject = "Discussion updates - Naglasúpan"
        email = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient.email],
        )
        email.attach_alternative(html, "text/html")
        try:
            email.send(fail_silently=False)
        except Exception:
            _log_sent_email(
                recipient=recipient,
                email_type=SentEmailType.DISCUSSION_DIGEST,
                subject=subject,
                to_email=recipient.email,
                success=False,
                error_message=f"Failed to send to {recipient.email}",
            )
            raise
        _log_sent_email(
            recipient=recipient,
            email_type=SentEmailType.DISCUSSION_DIGEST,
            subject=subject,
            to_email=recipient.email,
        )
