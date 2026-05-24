from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.articles.models import Article
from apps.discussions.models import Discussion
from apps.follows.models import FollowChannelPreference
from apps.notifications.models import Notification, NotificationCadence
from services.notifications import (
    NotificationGroup,
    NotificationGroupKind,
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
        kind=NotificationGroupKind.DISCUSSION,
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


def _build_article_group(rows: list[Notification]) -> NotificationGroup:
    from services import REPO  # noqa: PLC0415

    rows = sorted(
        rows,
        key=lambda n: n.article.published_at or n.created_at,
        reverse=True,
    )
    latest = rows[0]
    article = latest.article
    project = article.project
    return NotificationGroup(
        kind=NotificationGroupKind.ARTICLE,
        project=NotificationProject(
            id=project.id,
            slug=project.slug,
            title=project.title,
            image_url=REPO.project.get_project_icon_url(project),
        ),
        latest_event_at=article.published_at or latest.created_at,
        unread_count=len(rows),
        latest_body_excerpt=_body_excerpt(article.body),
        article_id=article.id,
        article_slug=article.slug,
        article_title=article.title,
        channel_name=article.channel.name,
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
            notification, created = Notification.objects.get_or_create(
                recipient=recipient,
                discussion=discussion,
                defaults={"email_cadence": recipient.notification_frequency},
            )

            if created and notification.email_cadence == NotificationCadence.IMMEDIATE:
                self._send_immediate(notification, discussion)

    def create_notifications_for_article(self, article_id: UUID) -> None:
        """Fan out notifications for a published article.

        Gating (e.g. backdated-publish suppression) is the caller's job —
        HANDLERS.articles.publish owns that decision and only invokes this
        method when fan-out is wanted. We still defensively check the
        article exists and is in `published` state.
        """
        try:
            article = Article.objects.select_related(
                "project", "channel", "author"
            ).get(pk=article_id)
        except Article.DoesNotExist:
            logger.warning("Article %s not found for notification", article_id)
            return

        if article.state != "published":
            return

        # Find every Follow on this project with a ChannelPreference for the
        # article's channel where at least one of the switches is on. Author
        # is excluded — no self-notification on publish.
        prefs = (
            FollowChannelPreference.objects.select_related("follow", "follow__user")
            .filter(
                follow__project_id=article.project_id,
                channel_id=article.channel_id,
            )
            .filter(follow__user__is_active=True)
        )

        author_id = article.author_id

        for pref in prefs:
            user = pref.follow.user
            if author_id is not None and user.pk == author_id:
                continue
            if not (pref.email_enabled or pref.in_app_enabled):
                continue

            # The Notification row carries both in-app state and email-send
            # bookkeeping. When email is on but in-app is off we still need
            # the row to drive the digest / immediate-send paths, so we
            # mark it already-read so it never surfaces in-app.
            notification, created = Notification.objects.get_or_create(
                recipient=user,
                article=article,
                defaults={
                    "email_cadence": user.notification_frequency,
                    "in_app_read_at": (None if pref.in_app_enabled else timezone.now()),
                },
            )
            if not created:
                continue

            if (
                pref.email_enabled
                and notification.email_cadence == NotificationCadence.IMMEDIATE
            ):
                self._send_article_immediate(notification, article)

    def _send_article_immediate(
        self, notification: Notification, article: Article
    ) -> None:
        from services import HANDLERS  # noqa: PLC0415

        try:
            HANDLERS.email.send_article_notification_email(
                notification=notification,
                article=article,
            )
            notification.email_sent = True
            notification.email_sent_at = timezone.now()
            notification.save(update_fields=["email_sent", "email_sent_at"])
        except Exception:
            logger.exception(
                "Failed to send immediate article notification %s", notification.id
            )

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
        # Discussion-row digest path. Article rows are picked up separately —
        # the existing discussion_digest template renders only comment-shaped
        # items and the recipient currently gets two digest emails when both
        # kinds are pending. Unifying into one mixed-content email is a
        # follow-up (tracked in tasks 5.4 / 5.5 of add-article-authoring).
        unsent = (
            Notification.objects.filter(
                email_cadence=cadence,
                email_sent=False,
                in_app_read_at__isnull=True,
                recipient__is_active=True,
                discussion__isnull=False,
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

        # Article-row digest path. Until the mixed-content template lands
        # this fires a separate per-recipient email for article batches.
        self._send_article_batch(cadence)

    def _send_article_batch(self, cadence: str) -> None:
        unsent = (
            Notification.objects.filter(
                email_cadence=cadence,
                email_sent=False,
                in_app_read_at__isnull=True,
                recipient__is_active=True,
                article__isnull=False,
            )
            .select_related(
                "recipient",
                "article",
                "article__project",
                "article__channel",
            )
            .order_by("recipient_id", "created_at")
        )

        from services import HANDLERS  # noqa: PLC0415

        for notification in unsent:
            try:
                HANDLERS.email.send_article_notification_email(
                    notification=notification,
                    article=notification.article,
                )
                notification.email_sent = True
                notification.email_sent_at = timezone.now()
                notification.save(update_fields=["email_sent", "email_sent_at"])
            except Exception:
                logger.exception(
                    "Failed to send article digest entry %s", notification.id
                )

    def list_unread_groups_for_user(
        self, user_id: UUID, limit: int = 50
    ) -> list[NotificationGroup]:
        from services import REPO  # noqa: PLC0415

        discussion_rows = list(
            REPO.notifications.list_unread_for_user(user_id).prefetch_related(
                "discussion__project__images__variants"
            )
        )

        by_root: defaultdict[UUID, list[Notification]] = defaultdict(list)
        for r in discussion_rows:
            by_root[_root_id(r)].append(r)

        groups = [_build_group(rs, root_id) for root_id, rs in by_root.items()]

        article_rows = list(
            REPO.notifications.list_unread_articles_for_user(user_id).prefetch_related(
                "article__project__images__variants"
            )
        )
        by_article: defaultdict[UUID, list[Notification]] = defaultdict(list)
        for r in article_rows:
            by_article[r.article_id].append(r)
        groups.extend(_build_article_group(rs) for rs in by_article.values())

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

    def mark_thread_read_for_comment(self, user_id: UUID, comment_id: UUID) -> int:
        try:
            d = Discussion.objects.values("id", "parent_id").get(id=comment_id)
        except Discussion.DoesNotExist:
            return 0
        root_id = d["parent_id"] or d["id"]
        return self.mark_thread_read_for_user(user_id, root_id)

    def mark_article_read_for_user(self, user_id: UUID, article_id: UUID) -> int:
        return Notification.objects.filter(
            recipient_id=user_id,
            article_id=article_id,
            in_app_read_at__isnull=True,
        ).update(in_app_read_at=timezone.now())

    def mark_all_read_for_user(self, user_id: UUID) -> int:
        return Notification.objects.filter(
            recipient_id=user_id, in_app_read_at__isnull=True
        ).update(in_app_read_at=timezone.now())

    def delete_old_read_notifications(self) -> int:
        cutoff = timezone.now() - timedelta(days=_RETENTION_DAYS)
        deleted, _ = Notification.objects.filter(
            in_app_read_at__isnull=False, in_app_read_at__lt=cutoff
        ).delete()
        return deleted
