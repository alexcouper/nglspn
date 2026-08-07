from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from apps.emails.models import (
    BroadcastEmailRecipient,
    BroadcastEmailStatus,
    SentEmail,
    SentEmailType,
)
from services.articles.summary import derive_summary
from services.email import EMAIL_LOGO_URL
from services.email.handler_interface import EmailHandlerInterface

from . import render_email
from .query import DjangoEmailQuery

if TYPE_CHECKING:
    from collections.abc import Sequence

    from apps.articles.models import Article
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
    html_body: str = "",
    project: Project | None = None,
) -> None:
    try:
        SentEmail.objects.create(
            recipient=recipient,
            email_type=email_type,
            subject=subject,
            to_email=to_email,
            success=success,
            error_message=error_message,
            html_body=html_body,
            project=project,
        )
    except Exception:
        logger.exception("Failed to log sent email record for %s", to_email)


def build_digest_groups(notifications: Sequence[Notification]) -> list[dict]:
    """Group notifications by project for digest emails.

    Each group's CTA deep-links to the latest comment id in that project group,
    so the recipient lands on the most recent comment when they click through.
    """
    groups_dict: dict[str, dict] = {}
    for n in notifications:
        project = n.discussion.project
        project_key = str(project.id)
        slug_or_id = project.slug or project.id
        if project_key not in groups_dict:
            groups_dict[project_key] = {
                "project_title": project.title,
                "project_url": (
                    f"{settings.FRONTEND_URL}/projects/{slug_or_id}"
                    f"?comment={n.discussion_id}#discussions"
                ),
                "comment_count": 0,
                "_latest_created_at": n.discussion.created_at,
            }
        else:
            entry = groups_dict[project_key]
            if n.discussion.created_at > entry["_latest_created_at"]:
                entry["_latest_created_at"] = n.discussion.created_at
                entry["project_url"] = (
                    f"{settings.FRONTEND_URL}/projects/{slug_or_id}"
                    f"?comment={n.discussion_id}#discussions"
                )
        groups_dict[project_key]["comment_count"] += 1

    return [
        {k: v for k, v in g.items() if not k.startswith("_")}
        for g in groups_dict.values()
    ]


ARTICLE_DIGEST_EXCERPT_MAX = 500


def _digest_article_image_url(article: Article) -> str | None:
    from services import REPO  # noqa: PLC0415

    hero = article.listing_image
    if hero is not None:
        variants = list(hero.variants.all())
        thumb = next((v for v in variants if v.size == "thumb"), None)
        return thumb.url if thumb else hero.url
    return REPO.project.get_project_icon_url(article.project)


def build_article_digest_entries(notifications: Sequence[Notification]) -> list[dict]:
    """Build the per-article context entries for the article digest template."""
    entries = []
    for n in notifications:
        article = n.article
        project = article.project
        # Same excerpt the listing card shows: the email is plain text, so the
        # markdown body has to be flattened rather than pasted in raw.
        body_excerpt = article.summary or derive_summary(
            article.body or "", limit=ARTICLE_DIGEST_EXCERPT_MAX
        )
        project_slug_or_id = project.slug or project.id
        article_slug_or_id = article.slug or article.id
        entries.append(
            {
                "project_title": project.title,
                "project_url": (
                    f"{settings.FRONTEND_URL}/projects/{project_slug_or_id}"
                ),
                "channel_name": article.channel.name,
                "article_title": article.title,
                "article_image_url": _digest_article_image_url(article),
                "body_excerpt": body_excerpt,
                "article_url": (
                    f"{settings.FRONTEND_URL}/projects/{project_slug_or_id}"
                    f"/articles/{article_slug_or_id}"
                ),
            }
        )
    return entries


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
                html_body=html,
            )
            raise
        _log_sent_email(
            recipient=user,
            email_type=SentEmailType.VERIFICATION,
            subject=subject,
            to_email=user.email,
            html_body=html,
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
                html_body=html,
            )
            raise
        _log_sent_email(
            recipient=user,
            email_type=SentEmailType.PASSWORD_RESET,
            subject=subject,
            to_email=user.email,
            html_body=html,
        )

    def send_project_approved_email(self, project: Project, recipient: User) -> None:
        slug_or_id = project.slug or project.id
        context = {
            "user_name": recipient.first_name or "there",
            "project_title": project.title,
            "project_url": f"{settings.FRONTEND_URL}/projects/{slug_or_id}",
            "is_community_tipoff": project.is_community_tipoff,
            "logo_url": EMAIL_LOGO_URL,
            "current_year": timezone.now().year,
        }
        html, text = render_email("project_approved", context)

        subject = "Your project has been approved - Naglasúpan"
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
                email_type=SentEmailType.PROJECT_APPROVED,
                subject=subject,
                to_email=recipient.email,
                success=False,
                error_message=f"Failed to send to {recipient.email}",
                html_body=html,
                project=project,
            )
            raise
        _log_sent_email(
            recipient=recipient,
            email_type=SentEmailType.PROJECT_APPROVED,
            subject=subject,
            to_email=recipient.email,
            html_body=html,
            project=project,
        )

    def send_new_project_notification(
        self, project: Project, recipient_email: str
    ) -> None:
        creator = project.creator
        creator_name = creator.full_name or creator.email
        is_tipoff = project.is_community_tipoff
        context = {
            "project_title": project.title,
            "project_tagline": project.tagline,
            "project_description": project.description,
            "owner_name": creator_name,
            "owner_email": creator.email,
            "is_community_tipoff": is_tipoff,
            "logo_url": EMAIL_LOGO_URL,
            "current_year": timezone.now().year,
        }
        html, text = render_email("new_project_notification", context)

        if is_tipoff:
            subject = f"New tip-off submitted: {project.title} - Naglasúpan"
        else:
            subject = f"New project submitted: {project.title} - Naglasúpan"
        email = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        email.attach_alternative(html, "text/html")
        try:
            email.send(fail_silently=False)
        except Exception:
            _log_sent_email(
                recipient=None,
                email_type=SentEmailType.NEW_PROJECT_NOTIFICATION,
                subject=subject,
                to_email=recipient_email,
                success=False,
                error_message=f"Failed to send to {recipient_email}",
                html_body=html,
            )
            raise
        _log_sent_email(
            recipient=None,
            email_type=SentEmailType.NEW_PROJECT_NOTIFICATION,
            subject=subject,
            to_email=recipient_email,
            html_body=html,
        )

    def send_broadcast(
        self,
        broadcast: BroadcastEmail,
        sent_by_user: User,
    ) -> tuple[int, int]:
        broadcast.status = BroadcastEmailStatus.SENDING
        broadcast.save(update_fields=["status"])

        success_count = 0
        failure_count = 0

        try:
            query = DjangoEmailQuery()
            html, text = query.render_broadcast_email(broadcast)
            recipients = query.resolve_broadcast_recipients(broadcast)

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
        except Exception:
            broadcast.status = BroadcastEmailStatus.FAILED
            broadcast.save(update_fields=["status"])
            raise

        broadcast.status = BroadcastEmailStatus.SENT
        broadcast.sent_at = timezone.now()
        broadcast.sent_by = sent_by_user
        broadcast.save(update_fields=["status", "sent_at", "sent_by"])

        return success_count, failure_count

    def send_discussion_notification_email(
        self, notification: Notification, discussion: Discussion
    ) -> None:
        author_name = "Someone"
        if discussion.author:
            author_name = discussion.author.full_name or discussion.author.email

        recipient = notification.recipient
        slug_or_id = discussion.project.slug or discussion.project.id
        context = {
            "recipient_name": recipient.first_name or "there",
            "author_name": author_name,
            "author_initial": author_name[0].upper() if author_name else "?",
            "project_title": discussion.project.title,
            "comment_body": discussion.body[:500],
            "project_url": (f"{settings.FRONTEND_URL}/projects/{slug_or_id}"),
            "discussion_url": (
                f"{settings.FRONTEND_URL}/projects/{slug_or_id}"
                f"?comment={discussion.id}#discussions"
            ),
            "profile_url": f"{settings.FRONTEND_URL}/profile",
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
                html_body=html,
            )
            raise
        _log_sent_email(
            recipient=recipient,
            email_type=SentEmailType.DISCUSSION_NOTIFICATION,
            subject=subject,
            to_email=recipient.email,
            html_body=html,
        )

    def send_discussion_digest_email(
        self, notifications: Sequence[Notification]
    ) -> None:
        if not notifications:
            return

        recipient = notifications[0].recipient

        context = {
            "recipient_name": recipient.first_name or "there",
            "groups": build_digest_groups(notifications),
            "site_url": settings.FRONTEND_URL,
            "profile_url": f"{settings.FRONTEND_URL}/profile",
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
                html_body=html,
            )
            raise
        _log_sent_email(
            recipient=recipient,
            email_type=SentEmailType.DISCUSSION_DIGEST,
            subject=subject,
            to_email=recipient.email,
            html_body=html,
        )

    def send_article_digest_email(self, notifications: Sequence[Notification]) -> None:
        if not notifications:
            return

        recipient = notifications[0].recipient

        context = {
            "recipient_name": recipient.first_name or "there",
            "entries": build_article_digest_entries(notifications),
            "site_url": settings.FRONTEND_URL,
            "profile_url": f"{settings.FRONTEND_URL}/profile",
            "logo_url": f"{settings.S3_PUBLIC_URL_BASE}/email/logo.png",
            "current_year": timezone.now().year,
        }
        html, text = render_email("article_digest", context)

        subject = "New articles - Naglasúpan"
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
                email_type=SentEmailType.ARTICLE_DIGEST,
                subject=subject,
                to_email=recipient.email,
                success=False,
                error_message=f"Failed to send to {recipient.email}",
                html_body=html,
            )
            raise
        _log_sent_email(
            recipient=recipient,
            email_type=SentEmailType.ARTICLE_DIGEST,
            subject=subject,
            to_email=recipient.email,
            html_body=html,
        )
