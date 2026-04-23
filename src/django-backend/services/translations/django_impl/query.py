from __future__ import annotations

from django.db.models import Max

from apps.translations.models import Translation, TranslationAudit
from services.translations.query_interface import (
    AuditEntry,
    TranslationDetail,
    TranslationQueryInterface,
)


class DjangoTranslationQuery(TranslationQueryInterface):
    def get_catalog(self, locale: str) -> dict[str, str]:
        rows = Translation.objects.filter(locale=locale, retired=False).values_list(
            "key", "text"
        )
        return dict(rows)

    def get_catalog_version(self, locale: str) -> int:
        max_updated = Translation.objects.filter(locale=locale).aggregate(
            m=Max("updated_at")
        )["m"]
        return int(max_updated.timestamp()) if max_updated else 0

    def get_detail(
        self, locale: str, key: str, history_limit: int = 10
    ) -> TranslationDetail:
        row = Translation.objects.filter(locale=locale, key=key).first()
        history_qs = (
            TranslationAudit.objects.filter(locale=locale, key=key)
            .select_related("changed_by")
            .order_by("-changed_at")[:history_limit]
        )
        history = [
            AuditEntry(
                changed_at=a.changed_at,
                changed_by=_display_name(a.changed_by) if a.changed_by else None,
                old_text=a.old_text,
                new_text=a.new_text,
            )
            for a in history_qs
        ]
        if row is None:
            return TranslationDetail(
                locale=locale, key=key, text="", updated_at=None, history=history
            )
        return TranslationDetail(
            locale=locale,
            key=key,
            text=row.text,
            updated_at=row.updated_at,
            history=history,
        )


def _display_name(user: object) -> str:
    full = f"{user.first_name} {user.last_name}".strip()  # type: ignore[attr-defined]
    return full or user.email  # type: ignore[attr-defined,no-any-return]
