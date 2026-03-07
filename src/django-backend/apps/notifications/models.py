import uuid

from django.conf import settings
from django.db import models


class NotificationCadence(models.TextChoices):
    IMMEDIATE = "immediate", "Every Time"
    HOURLY = "hourly", "At most every hour"
    DAILY = "daily", "At most every day"
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
        related_name="notifications",
    )
    cadence = models.CharField(
        max_length=20,
        choices=NotificationCadence.choices,
    )
    sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notification for {self.recipient} re: {self.discussion_id}"
