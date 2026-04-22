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
