"""Article routes addressed by id alone, for both kinds of article.

Mounted at `/api/articles`. Authorisation is derived from the article — its
author for an author-owned one, a `full_edit` contributor for one on a project
— so the editor needs no project slug and an author-owned article has a home.
Creation and reads by slug stay per container (`articles.py`, `users.py`,
`auth.py`). A caller without rights gets 404, never 403: the id leaks nothing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 - needed at runtime for ninja path params

from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.routers._helpers import resolve_editable_article_or_404
from api.schemas.article import (
    ArticleImageUploadRequest,
    ArticleOut,
    ArticlePublish,
    ArticleUpdate,
)
from api.schemas.errors import Error
from api.schemas.project import (
    ImageResponse,
    ImageUploadCompleteRequest,
    PresignedUploadResponse,
)
from apps.projects.models import UploadStatus
from services import HANDLERS, REPO
from services.articles.exceptions import (
    ArticleError,
    ArticleNotFoundError,
    ArticleNotPublishableError,
    ChannelNotFoundError,
    ChannelOnWrongProjectError,
    InvalidCropError,
    ListingImageNotUploadedError,
    ListingImageOnWrongProjectError,
    NoChannelForAuthorArticleError,
)
from services.articles.handler_interface import UNSET
from services.images.exceptions import ImageError
from services.images.handler_interface import FileMeta

if TYPE_CHECKING:
    from apps.articles.models import Article
    from apps.projects.models import Image

router = Router()


@router.get(
    "/{article_id}",
    response={200: ArticleOut, 401: Error, 404: Error},
    auth=auth,
    tags=["Articles"],
)
def get_article(
    request: HttpRequest,
    article_id: UUID,
) -> Article | tuple[int, dict[str, str]]:
    """The editor's read: the article as its author or a contributor sees it,
    whatever its state or visibility."""
    return resolve_editable_article_or_404(article_id, request.auth.id)


# Domain errors update_article can raise, and how each surfaces to the client.
# A mapping rather than a stack of except arms so adding a case does not push
# the view past ruff's return-statement limit.
_PATCH_ARTICLE_ERRORS: dict[type[ArticleError], tuple[int, str]] = {
    ArticleNotFoundError: (404, "Article not found"),
    ChannelNotFoundError: (404, "Channel not found on this project"),
    ChannelOnWrongProjectError: (404, "Channel not found on this project"),
    NoChannelForAuthorArticleError: (
        422,
        "An article published under your own name has no channel to choose",
    ),
    ListingImageOnWrongProjectError: (
        422,
        "Listing image must belong to this article or its project",
    ),
    ListingImageNotUploadedError: (
        422,
        "Listing image upload has not completed",
    ),
    InvalidCropError: (422, "Image framing is not a valid crop of this image"),
}


@router.patch(
    "/{article_id}",
    response={200: ArticleOut, 401: Error, 404: Error, 422: Error},
    auth=auth,
    tags=["Articles"],
)
def patch_article(
    request: HttpRequest,
    article_id: UUID,
    payload: ArticleUpdate,
) -> Article | tuple[int, dict[str, str]]:
    existing = resolve_editable_article_or_404(article_id, request.auth.id)
    if isinstance(existing, tuple):
        return existing
    # A PATCH body cannot express "clear the listing image" with null alone,
    # because an omitted optional field deserialises to null too. Only forward
    # the key the client actually sent; everything else stays UNSET.
    provided = payload.dict(exclude_unset=True)
    try:
        article = HANDLERS.articles.update_article(
            article_id,
            title=payload.title,
            body=payload.body,
            summary=payload.summary,
            listing_image_id=provided.get("listing_image_id", UNSET),
            listing_crop=provided.get("listing_crop", UNSET),
            channel_id=payload.channel_id,
            published_at=payload.published_at,
        )
    except ArticleError as exc:
        mapped = _PATCH_ARTICLE_ERRORS.get(type(exc))
        if mapped is None:
            raise
        status, detail = mapped
        return status, {"detail": detail}
    return article


@router.post(
    "/{article_id}/publish",
    response={200: ArticleOut, 401: Error, 404: Error, 422: Error},
    auth=auth,
    tags=["Articles"],
)
def publish_article(
    request: HttpRequest,
    article_id: UUID,
    payload: ArticlePublish,
) -> Article | tuple[int, dict[str, str]]:
    existing = resolve_editable_article_or_404(article_id, request.auth.id)
    if isinstance(existing, tuple):
        return existing
    try:
        article = HANDLERS.articles.publish(
            article_id, published_at=payload.published_at
        )
    except ArticleNotFoundError:
        return 404, {"detail": "Article not found"}
    except ArticleNotPublishableError:
        return 422, {"detail": "Article requires a title and body to publish"}
    return article


@router.delete(
    "/{article_id}",
    response={204: None, 401: Error, 404: Error},
    auth=auth,
    tags=["Articles"],
)
def delete_article(
    request: HttpRequest,
    article_id: UUID,
) -> tuple[int, None] | tuple[int, dict[str, str]]:
    existing = resolve_editable_article_or_404(article_id, request.auth.id)
    if isinstance(existing, tuple):
        return existing
    HANDLERS.articles.delete_article(article_id)
    return 204, None


# ----------------------------------------------------------------------
# Article images
#
# The rows live on `Image` so they share the storage and variant pipeline,
# but they are addressed here because they belong to an article. Ownership is
# the same `resolve_editable_article_or_404` the rest of this router uses.
# ----------------------------------------------------------------------


def _get_article_image_or_404(
    article: Article, image_id: UUID, *, status: UploadStatus | None = None
) -> Image | tuple[int, dict[str, str]]:
    image = REPO.images.get_article_image(article, image_id, status=status)
    if image is None:
        return 404, {"detail": "Image not found"}
    return image


@router.post(
    "/{article_id}/images/upload-url",
    response={200: PresignedUploadResponse, 400: Error, 401: Error, 404: Error},
    auth=auth,
    tags=["Article Images"],
)
def get_article_image_upload_url(
    request: HttpRequest,
    article_id: UUID,
    payload: ArticleImageUploadRequest,
) -> PresignedUploadResponse | tuple[int, dict[str, str]]:
    article = resolve_editable_article_or_404(article_id, request.auth.id)
    if isinstance(article, tuple):
        return article

    try:
        prepared = HANDLERS.images.create_article_upload(
            article,
            FileMeta(
                filename=payload.filename,
                content_type=payload.content_type,
                file_size=payload.file_size,
            ),
        )
    except ImageError as exc:
        return 400, {"detail": str(exc)}

    return PresignedUploadResponse(
        image_id=prepared.image.id,
        upload_url=prepared.upload_url,
        method=prepared.method,
        headers=prepared.headers,
        storage_key=prepared.storage_key,
    )


@router.post(
    "/{article_id}/images/{image_id}/complete",
    response={200: ImageResponse, 400: Error, 401: Error, 404: Error},
    auth=auth,
    tags=["Article Images"],
)
def complete_article_image_upload(
    request: HttpRequest,
    article_id: UUID,
    image_id: UUID,
    payload: ImageUploadCompleteRequest,
) -> Image | tuple[int, dict[str, str]]:
    article = resolve_editable_article_or_404(article_id, request.auth.id)
    if isinstance(article, tuple):
        return article

    image = _get_article_image_or_404(article, image_id, status=UploadStatus.PENDING)
    if isinstance(image, tuple):
        return image

    try:
        return HANDLERS.images.complete_upload(
            image, width=payload.width, height=payload.height
        )
    except ImageError as exc:
        return 400, {"detail": str(exc)}


@router.delete(
    "/{article_id}/images/{image_id}",
    response={204: None, 401: Error, 404: Error},
    auth=auth,
    tags=["Article Images"],
)
def delete_article_image(
    request: HttpRequest,
    article_id: UUID,
    image_id: UUID,
) -> tuple[int, None] | tuple[int, dict[str, str]]:
    article = resolve_editable_article_or_404(article_id, request.auth.id)
    if isinstance(article, tuple):
        return article

    image = _get_article_image_or_404(article, image_id)
    if isinstance(image, tuple):
        return image

    HANDLERS.images.delete_image(image)
    return 204, None
