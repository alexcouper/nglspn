from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.schemas.errors import Error
from api.schemas.translations import (
    TranslationPatchRequest,
    TranslationResponse,
    TranslationVersionResponse,
)
from services import HANDLERS, REPO

router = Router()


@router.get("/{locale}", response=dict[str, str], tags=["Translations"])
def get_catalog(request: HttpRequest, locale: str) -> dict[str, str]:
    """Return the full non-retired translation catalog for a locale."""
    return REPO.translations.get_catalog(locale)


@router.get(
    "/{locale}/version",
    response=TranslationVersionResponse,
    tags=["Translations"],
)
def get_version(request: HttpRequest, locale: str) -> dict[str, int]:
    """Return a monotonic version for a locale's catalog (max updated_at as epoch)."""
    return {"version": REPO.translations.get_catalog_version(locale)}


@router.patch(
    "/{locale}/{key}",
    response={200: TranslationResponse, 401: Error},
    auth=auth,
    tags=["Translations"],
)
def patch_translation(
    request: HttpRequest,
    locale: str,
    key: str,
    payload: TranslationPatchRequest,
) -> TranslationResponse:
    """Edit a translation. Creates the row if missing. Requires authentication."""
    return HANDLERS.translations.update_text(
        locale=locale, key=key, text=payload.text, user=request.auth
    )
