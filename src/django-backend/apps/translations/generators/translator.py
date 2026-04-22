from __future__ import annotations

import os
from typing import Protocol

import requests


class Translator(Protocol):
    def translate(
        self, text: str, *, target_locale: str, source_locale: str = "en"
    ) -> str: ...


class MissingCredentialsError(RuntimeError):
    pass


class DeepLTranslator:
    """Thin wrapper around the DeepL REST API.

    Uses DEEPL_AUTH_KEY from the environment. DeepL free tier lives at
    api-free.deepl.com; pro at api.deepl.com. The key's suffix (":fx") tells
    us which endpoint to use.
    """

    TIMEOUT_SECONDS = 30

    def __init__(self, auth_key: str | None = None) -> None:
        key = auth_key or os.environ.get("DEEPL_AUTH_KEY")
        if not key:
            msg = (
                "DEEPL_AUTH_KEY is not set. Get one at https://www.deepl.com/pro-api "
                "and export it before running `make translate-new-keys`."
            )
            raise MissingCredentialsError(msg)
        self._key = key
        self._base = (
            "https://api-free.deepl.com/v2"
            if key.endswith(":fx")
            else "https://api.deepl.com/v2"
        )

    def translate(
        self, text: str, *, target_locale: str, source_locale: str = "en"
    ) -> str:
        response = requests.post(
            f"{self._base}/translate",
            data={
                "text": text,
                "source_lang": source_locale.upper(),
                "target_lang": target_locale.upper(),
                "preserve_formatting": "1",
                "tag_handling": "xml",
                "ignore_tags": "icu",
            },
            headers={"Authorization": f"DeepL-Auth-Key {self._key}"},
            timeout=self.TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        return data["translations"][0]["text"]


class StubTranslator:
    """Deterministic translator used in tests. Returns f'[target_locale] text'."""

    def translate(
        self, text: str, *, target_locale: str, source_locale: str = "en"
    ) -> str:
        return f"[{target_locale}] {text}"
