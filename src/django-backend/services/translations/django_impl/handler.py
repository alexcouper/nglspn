from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apps.translations.models import Translation
from apps.translations.webhooks import notify_web_ui
from services.translations.handler_interface import TranslationHandlerInterface

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

logger = logging.getLogger(__name__)


class DjangoTranslationHandler(TranslationHandlerInterface):
    def update_text(
        self,
        locale: str,
        key: str,
        text: str,
        user: AbstractBaseUser,
    ) -> Translation:
        try:
            t = Translation.objects.get(locale=locale, key=key)
            t.text = text
            t.is_machine_translated = False
            t.updated_by = user
            t.save()
        except Translation.DoesNotExist:
            t = Translation.objects.create(
                locale=locale,
                key=key,
                text=text,
                source_hash="",
                is_machine_translated=False,
                updated_by=user,
            )

        try:
            notify_web_ui(locale)
        except Exception as exc:  # noqa: BLE001 - defensive; notify_web_ui already swallows
            logger.warning("notify_web_ui raised unexpectedly: %s", exc)

        return t
