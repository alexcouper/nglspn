from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from apps.translations.models import Translation, TranslationAudit


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    list_display = ("locale", "key", "is_machine_translated", "retired", "updated_at")
    list_filter = ("locale", "is_machine_translated", "retired")
    search_fields = ("key", "text")
    readonly_fields = ("updated_at", "source_hash")


@admin.register(TranslationAudit)
class TranslationAuditAdmin(admin.ModelAdmin):
    list_display = ("locale", "key", "changed_by", "changed_at")
    list_filter = ("locale",)
    search_fields = ("key", "old_text", "new_text")
    readonly_fields = tuple(
        f.name
        for f in TranslationAudit._meta.fields  # noqa: SLF001
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
