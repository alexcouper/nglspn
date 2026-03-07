from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.discussions.models import Discussion
from apps.notifications.models import Notification, NotificationCadence
from services.notifications.handler_interface import NotificationHandlerInterface

if TYPE_CHECKING:
    from uuid import UUID

    from apps.users.models import User

logger = logging.getLogger(__name__)


class DjangoNotificationHandler(NotificationHandlerInterface):
    def create_notifications_for_discussion(self, discussion_id: UUID) -> None:
        try:
            discussion = Discussion.objects.select_related(
                "project__owner", "author", "parent"
            ).get(id=discussion_id)
        except Discussion.DoesNotExist:
            logger.warning("Discussion %s not found for notification", discussion_id)
            return

        recipients: set[User] = set()

        # 1. Project owner
        project_owner = discussion.project.owner
        if project_owner:
            recipients.add(project_owner)

        # 2. Root discussion author (if this is a reply)
        root = discussion.parent if discussion.parent else discussion
        if discussion.parent and root.author:
            recipients.add(root.author)

        # 3. All previous participants in the root discussion thread
        participant_ids = (
            Discussion.objects.filter(parent=root)
            .exclude(author__isnull=True)
            .values_list("author_id", flat=True)
            .distinct()
        )
        from apps.users.models import User as UserModel  # noqa: PLC0415

        participants = UserModel.objects.filter(id__in=participant_ids)
        recipients.update(participants)

        # Exclude the comment author
        if discussion.author:
            recipients.discard(discussion.author)

        # Skip users with NEVER cadence, create notifications for the rest
        for recipient in recipients:
            if recipient.notification_frequency == NotificationCadence.NEVER:
                continue

            notification = Notification.objects.create(
                recipient=recipient,
                discussion=discussion,
                cadence=recipient.notification_frequency,
            )

            if notification.cadence == NotificationCadence.IMMEDIATE:
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
            notification.sent = True
            notification.sent_at = timezone.now()
            notification.save(update_fields=["sent", "sent_at"])
        except Exception:
            logger.exception(
                "Failed to send immediate notification %s", notification.id
            )

    def send_immediate_notifications(self) -> None:
        unsent = Notification.objects.filter(
            cadence=NotificationCadence.IMMEDIATE, sent=False
        ).select_related("recipient", "discussion", "discussion__project")

        for notification in unsent:
            self._send_immediate(notification, notification.discussion)

    def send_batch_notifications(self, cadence: str) -> None:
        unsent = (
            Notification.objects.filter(cadence=cadence, sent=False)
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
                    notification.sent = True
                    notification.sent_at = now
                Notification.objects.bulk_update(notifications, ["sent", "sent_at"])
            except Exception:
                logger.exception("Failed to send digest to user %s", _recipient_id)
