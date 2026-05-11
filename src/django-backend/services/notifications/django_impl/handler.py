from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.discussions.models import Discussion
from apps.notifications.models import Notification, NotificationCadence
from services.notifications import (
    NotificationGroup,
    NotificationHeadlineKind,
    NotificationProject,
    NotificationSummary,
)
from services.notifications.handler_interface import NotificationHandlerInterface

if TYPE_CHECKING:
    from collections.abc import Iterable
    from uuid import UUID

    from apps.users.models import User

logger = logging.getLogger(__name__)

_BODY_EXCERPT_MAX = 240
_RETENTION_DAYS = 30


def _root_id(notification: Notification) -> UUID:
    return notification.discussion.parent_id or notification.discussion_id


def _actor_name(user: User | None) -> str:
    if user is None:
        return "Someone"
    if user.full_name:
        return user.full_name
    return user.first_name or user.email or "Someone"


def _body_excerpt(text: str) -> str:
    text = text.strip()
    if len(text) <= _BODY_EXCERPT_MAX:
        return text
    return text[:_BODY_EXCERPT_MAX].rstrip() + "…"


def _build_group(rows: Iterable[Notification], root_id: UUID) -> NotificationGroup:
    from services import REPO  # noqa: PLC0415

    rows = sorted(rows, key=lambda n: n.discussion.created_at, reverse=True)
    latest = rows[0]
    project = latest.discussion.project

    headline_kind = NotificationHeadlineKind.STARTED
    for r in rows:
        if r.discussion.parent_id is not None:
            headline_kind = NotificationHeadlineKind.REPLIED
            break

    actor_names: list[str] = []
    seen: set[str] = set()
    for r in rows:
        name = _actor_name(r.discussion.author)
        if name not in seen:
            seen.add(name)
            actor_names.append(name)

    return NotificationGroup(
        root_discussion_id=root_id,
        project=NotificationProject(
            id=project.id,
            slug=project.slug,
            title=project.title,
            image_url=REPO.project.get_project_icon_url(project),
        ),
        headline_kind=headline_kind,
        actor_names=actor_names,
        latest_body_excerpt=_body_excerpt(latest.discussion.body),
        latest_event_at=latest.discussion.created_at,
        unread_count=len(rows),
        latest_comment_id=latest.discussion_id,
    )


class DjangoNotificationHandler(NotificationHandlerInterface):
    def create_notifications_for_discussion(self, discussion_id: UUID) -> None:
        try:
            discussion = Discussion.objects.select_related(
                "project", "author", "parent"
            ).get(id=discussion_id)
        except Discussion.DoesNotExist:
            logger.warning("Discussion %s not found for notification", discussion_id)
            return

        recipients: set[User] = set()

        from services import REPO  # noqa: PLC0415

        for contributor in REPO.project.list_notifiable_contributors(
            discussion.project.id
        ):
            if contributor.user and contributor.user.is_active:
                recipients.add(contributor.user)

        root = discussion.parent if discussion.parent else discussion
        if discussion.parent and root.author and root.author.is_active:
            recipients.add(root.author)

        participant_ids = (
            Discussion.objects.filter(parent=root)
            .exclude(author__isnull=True)
            .values_list("author_id", flat=True)
            .distinct()
        )
        from apps.users.models import User as UserModel  # noqa: PLC0415

        participants = UserModel.objects.filter(id__in=participant_ids, is_active=True)
        recipients.update(participants)

        # Exclude the comment author
        if discussion.author:
            recipients.discard(discussion.author)

        for recipient in recipients:
            notification = Notification.objects.create(
                recipient=recipient,
                discussion=discussion,
                email_cadence=recipient.notification_frequency,
            )

            if notification.email_cadence == NotificationCadence.IMMEDIATE:
                self._send_immediate(notification, discussion)

    def _send_immediate(
        self, notification: Notification, discussion: Discussion
    ) -> None:
        from services import HANDLERS  # noqa: PLC0415

        try:
            HANDLERS.email.send_discussion_notification_email(
                notification=notification,
                discussion=discussion,
            )
            notification.email_sent = True
            notification.email_sent_at = timezone.now()
            notification.save(update_fields=["email_sent", "email_sent_at"])
        except Exception:
            logger.exception(
                "Failed to send immediate notification %s", notification.id
            )

    def send_batch_notifications(self, cadence: str) -> None:
        unsent = (
            Notification.objects.filter(
                email_cadence=cadence,
                email_sent=False,
                in_app_read_at__isnull=True,
                recipient__is_active=True,
            )
            .select_related(
                "recipient",
                "discussion",
                "discussion__project",
                "discussion__author",
            )
            .order_by("recipient_id", "created_at")
        )

        # Group by recipient
        by_recipient: defaultdict[UUID, list[Notification]] = defaultdict(list)
        for notification in unsent:
            by_recipient[notification.recipient_id].append(notification)

        from services import HANDLERS  # noqa: PLC0415

        for _recipient_id, notifications in by_recipient.items():
            try:
                HANDLERS.email.send_discussion_digest_email(
                    notifications=notifications,
                )
                now = timezone.now()
                for notification in notifications:
                    notification.email_sent = True
                    notification.email_sent_at = now
                Notification.objects.bulk_update(
                    notifications, ["email_sent", "email_sent_at"]
                )
            except Exception:
                logger.exception("Failed to send digest to user %s", _recipient_id)

    def list_unread_groups_for_user(
        self, user_id: UUID, limit: int = 50
    ) -> list[NotificationGroup]:
        from services import REPO  # noqa: PLC0415

        rows = list(
            REPO.notifications.list_unread_for_user(user_id).prefetch_related(
                "discussion__project__images__variants"
            )
        )

        by_root: defaultdict[UUID, list[Notification]] = defaultdict(list)
        for r in rows:
            by_root[_root_id(r)].append(r)

        groups = [_build_group(rs, root_id) for root_id, rs in by_root.items()]
        groups.sort(key=lambda g: g.latest_event_at, reverse=True)
        return groups[:limit]

    def get_unread_summary_for_user(self, user_id: UUID) -> NotificationSummary:
        from services import REPO  # noqa: PLC0415

        count = REPO.notifications.count_unread_groups_for_user(user_id)
        return NotificationSummary(has_unread=count > 0, unread_group_count=count)

    def mark_thread_read_for_user(self, user_id: UUID, root_discussion_id: UUID) -> int:
        from services import REPO  # noqa: PLC0415

        return REPO.notifications.unread_rows_for_thread(
            user_id, root_discussion_id
        ).update(in_app_read_at=timezone.now())

    def delete_old_read_notifications(self) -> int:
        cutoff = timezone.now() - timedelta(days=_RETENTION_DAYS)
        deleted, _ = Notification.objects.filter(
            in_app_read_at__isnull=False, in_app_read_at__lt=cutoff
        ).delete()
        return deleted
