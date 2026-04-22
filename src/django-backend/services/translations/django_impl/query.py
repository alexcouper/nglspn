from __future__ import annotations

from django.db.models import Max

from apps.translations.models import Translation
from services.translations.query_interface import TranslationQueryInterface


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
