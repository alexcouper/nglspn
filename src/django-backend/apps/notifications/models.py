import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class NotificationCadence(models.TextChoices):
    # Union of per-kind cadence values. A Notification row snapshots its
    # recipient's kind-appropriate User cadence (DiscussionEmailFrequency or
    # ArticleEmailFrequency); both feed values into this column. `immediate` is
    # discussion-only; `weekly` is article-only.
    IMMEDIATE = "immediate", "Every Time"
    HOURLY = "hourly", "At most every hour"
    DAILY = "daily", "At most every day"
    WEEKLY = "weekly", "At most every week"
    NEVER = "never", "Never"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    discussion = models.ForeignKey(
        "discussions.Discussion",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    article = models.ForeignKey(
        "articles.Article",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    email_cadence = models.CharField(
        max_length=20,
        choices=NotificationCadence.choices,
    )
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    in_app_read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient", "in_app_read_at"],
                name="notifications_recip_inapp_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "discussion"],
                condition=Q(discussion__isnull=False),
                name="notifications_recip_disc_uniq",
            ),
            models.UniqueConstraint(
                fields=["recipient", "article"],
                condition=Q(article__isnull=False),
                name="notifications_recip_article_uniq",
            ),
            # Exactly one of discussion / article SHALL be set.
            models.CheckConstraint(
                condition=(
                    Q(discussion__isnull=False, article__isnull=True)
                    | Q(discussion__isnull=True, article__isnull=False)
                ),
                name="notifications_target_xor",
            ),
        ]

    def __str__(self) -> str:
        target = (
            f"discussion {self.discussion_id}"
            if self.discussion_id
            else f"article {self.article_id}"
        )
        return f"Notification for {self.recipient} re: {target}"

    def save(self, *args: object, **kwargs: object) -> None:
        # SQLite parity for the XOR CHECK above.
        has_discussion = self.discussion_id is not None
        has_article = self.article_id is not None
        if has_discussion == has_article:
            msg = (
                "Notification MUST point at exactly one of discussion or "
                "article (got both set)"
                if has_discussion
                else "Notification MUST point at exactly one of discussion or "
                "article (got neither)"
            )
            raise ValidationError(msg)
        super().save(*args, **kwargs)
