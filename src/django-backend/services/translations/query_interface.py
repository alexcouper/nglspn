from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime  # noqa: TC003 - used at runtime by dataclass


@dataclass(frozen=True)
class AuditEntry:
    changed_at: datetime
    changed_by: str | None
    old_text: str
    new_text: str


@dataclass(frozen=True)
class TranslationDetail:
    locale: str
    key: str
    text: str
    updated_at: datetime | None
    history: list[AuditEntry]


class TranslationQueryInterface(ABC):
    @abstractmethod
    def get_catalog(self, locale: str) -> dict[str, str]:
        """Return {key: text} for all non-retired rows in `locale`."""

    @abstractmethod
    def get_catalog_version(self, locale: str) -> int:
        """Return the max updated_at for `locale` as an epoch int. 0 if empty."""

    @abstractmethod
    def get_detail(
        self, locale: str, key: str, history_limit: int = 10
    ) -> TranslationDetail:
        """Return current text + updated_at + last-N audit entries for (locale, key).
        If no row exists, returns empty text + None updated_at + empty history."""
