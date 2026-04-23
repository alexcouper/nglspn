from datetime import datetime

from ninja import Schema


class TranslationPatchRequest(Schema):
    text: str


class TranslationResponse(Schema):
    locale: str
    key: str
    text: str
    source_hash: str
    is_machine_translated: bool
    updated_at: datetime


class TranslationVersionResponse(Schema):
    version: int


class TranslationAuditEntryResponse(Schema):
    changed_at: datetime
    changed_by: str | None
    old_text: str
    new_text: str


class TranslationDetailResponse(Schema):
    locale: str
    key: str
    text: str
    updated_at: datetime | None
    history: list[TranslationAuditEntryResponse]
