import uuid

from django.conf import settings
from django.core.files.storage import Storage, storages
from django.db import models


class BroadcastEmailType(models.TextChoices):
    PLATFORM_UPDATES = "platform_updates", "Platform Updates"
    COMPETITION_RESULTS = "competition_results", "Competition Results"


class BroadcastEmail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.CharField(max_length=200)
    body_markdown = models.TextField(
        help_text=(
            "Write the email body in Markdown format. "
            "Upload images below, then click Insert to add them."
        ),
    )
    email_type = models.CharField(
        max_length=30,
        choices=BroadcastEmailType.choices,
        blank=True,
        null=True,
        help_text=(
            "If set, sends to all users opted in to this type. "
            "If blank, uses individual recipients below."
        ),
    )
    individual_recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="broadcast_emails_received",
        help_text="Select individual users (only used when email type is blank).",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="broadcast_emails_created",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="broadcast_emails_sent",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "broadcast_emails"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        status = "Sent" if self.sent_at else "Draft"
        return f"[{status}] {self.subject}"

    @property
    def is_sent(self) -> bool:
        return self.sent_at is not None


class BroadcastEmailRecipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    broadcast_email = models.ForeignKey(
        BroadcastEmail,
        on_delete=models.CASCADE,
        related_name="delivery_records",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="broadcast_deliveries",
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        db_table = "broadcast_email_recipients"
        unique_together = [("broadcast_email", "user")]

    def __str__(self) -> str:
        status = "OK" if self.success else "FAILED"
        return f"{self.user.email} - {status}"


def _broadcast_image_storage() -> Storage:
    return storages["broadcast_images"]


def _broadcast_image_upload_path(instance: "BroadcastEmailImage", filename: str) -> str:
    return f"{instance.id}/{filename}"


class BroadcastEmailImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    broadcast_email = models.ForeignKey(
        BroadcastEmail,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(
        upload_to=_broadcast_image_upload_path,
        storage=_broadcast_image_storage,
    )
    original_filename = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "broadcast_email_images"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return self.original_filename or str(self.id)

    def save(self, *args, **kwargs) -> None:
        if self.image and not self.original_filename:
            self.original_filename = self.image.name
        super().save(*args, **kwargs)

    @property
    def url(self) -> str:
        return self.image.url
