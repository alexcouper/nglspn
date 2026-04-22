from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from apps.translations.models import Translation


class TranslationHandlerInterface(ABC):
    @abstractmethod
    def update_text(
        self,
        locale: str,
        key: str,
        text: str,
        user: AbstractBaseUser,
    ) -> Translation:
        """Upsert a translation for (locale, key). Side effects:
        - flips `is_machine_translated` to False
        - writes audit (via Translation.save hook)
        - fires the web-ui revalidation webhook
        - sets updated_by to `user`
        Returns the updated/created Translation instance.
        """
