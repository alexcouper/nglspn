from django.conf import settings
from django.db import models


class Translation(models.Model):
    locale = models.CharField(max_length=16, db_index=True)
    key = models.CharField(max_length=255, db_index=True)
    text = models.TextField()
    source_hash = models.CharField(max_length=64)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="translations_edited",
    )
    updated_at = models.DateTimeField(auto_now=True)
    is_machine_translated = models.BooleanField(default=False)
    retired = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "key"], name="uniq_translation_locale_key"
            )
        ]
        indexes = [
            models.Index(fields=["locale", "retired"]),
        ]

    def __str__(self) -> str:
        return f"[{self.locale}] {self.key}"

    def save(self, *args, **kwargs) -> None:
        previous_text = ""
        if self.pk is not None:
            previous_text = (
                Translation.objects.filter(pk=self.pk)
                .values_list("text", flat=True)
                .first()
                or ""
            )
        super().save(*args, **kwargs)
        if previous_text != self.text:
            TranslationAudit.objects.create(
                translation=self,
                locale=self.locale,
                key=self.key,
                old_text=previous_text,
                new_text=self.text,
                changed_by=self.updated_by,
            )


class TranslationAudit(models.Model):
    translation = models.ForeignKey(
        Translation,
        on_delete=models.DO_NOTHING,
        related_name="audits",
    )
    locale = models.CharField(max_length=16)
    key = models.CharField(max_length=255)
    old_text = models.TextField(blank=True)
    new_text = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["translation", "changed_at"]),
            models.Index(fields=["locale", "key"]),
        ]

    def __str__(self) -> str:
        return f"[{self.locale}] {self.key} @ {self.changed_at:%Y-%m-%d %H:%M}"
