from __future__ import annotations

from abc import ABC, abstractmethod


class TranslationQueryInterface(ABC):
    @abstractmethod
    def get_catalog(self, locale: str) -> dict[str, str]:
        """Return {key: text} for all non-retired rows in `locale`."""

    @abstractmethod
    def get_catalog_version(self, locale: str) -> int:
        """Return the max updated_at for `locale` as an epoch int. 0 if empty."""
