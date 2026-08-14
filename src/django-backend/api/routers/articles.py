from uuid import UUID

from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.routers._helpers import (
    get_optional_user,
    require_full_edit,
    resolve_visible_project_or_404,
)
from api.schemas.article import (
    ArticleCreate,
    ArticleImageUploadRequest,
    ArticleListItem,
    ArticleOut,
    ArticlePublish,
    ArticleUpdate,
)
from api.schemas.errors import Error
from api.schemas.project import (
    ImageUploadCompleteRequest,
    PresignedUploadResponse,
    ProjectImageResponse,
)
from apps.articles.models import Article
from apps.projects.models import Project, ProjectImage, UploadStatus
from apps.users.models import User
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
)
from services.articles.handler_interface import UNSET
from services.images.exceptions import ImageError
from services.images.handler_interface import FileMeta

router = Router()


def _can_view_hidden(article: Article, user: User | None) -> bool:
    """Who may read an article the site is not showing globally.

    Authorisation, deliberately separate from `Article.is_globally_visible`:
    that answers "does this render for everyone", this answers "may this user
    see it anyway". Covers drafts, articles awaiting admin review and demoted
    articles alike — an author keeps access to their own work in edit mode
    whatever the site has decided about it.
    """
    if user is None:
        return False
    if article.author_id == user.id:
        return True
    return REPO.project.user_can_edit(article.project_id, user.id)


def _get_article_in_project(
    project: Project, article_id: UUID
) -> Article | tuple[int, dict[str, str]]:
    article = REPO.articles.get_by_id(article_id)
    if article is None or article.project_id != project.id:
        return 404, {"detail": "Article not found"}
    return article


@router.post(
    "/{slug}/articles",
    response={201: ArticleOut, 401: Error, 403: Error, 404: Error, 422: Error},
    auth=auth,
    tags=["Articles"],
)
def create_article(
    request: HttpRequest,
    slug: str,
    payload: ArticleCreate,
) -> tuple[int, Article] | tuple[int, dict[str, str]]:
    project = require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    try:
        article = HANDLERS.articles.create_draft(
            project_id=project.id,
            channel_id=payload.channel_id,
            author_id=request.auth.id,
            title=payload.title,
            body=payload.body,
        )
    except (ChannelNotFoundError, ChannelOnWrongProjectError):
        return 404, {"detail": "Channel not found on this project"}
    return 201, article


@router.get(
    "/{slug}/articles",
    response={200: list[ArticleListItem], 404: Error},
    tags=["Articles"],
)
def list_articles(
    request: HttpRequest,
    slug: str,
) -> list[Article] | tuple[int, dict[str, str]]:
    user = get_optional_user(request)
    project = resolve_visible_project_or_404(slug, user)
    if isinstance(project, tuple):
        return project
    # Edit rights are what the my-projects article table is fetched with, and
    # that table is where an author sees their drafts and anything held back
    # from global rendering.
    include_hidden = user is not None and REPO.project.user_can_edit(
        project.id, user.id
    )
    return list(REPO.articles.for_project(project.id, include_hidden=include_hidden))


@router.get(
    "/{slug}/articles/by-slug/{article_slug}",
    response={200: ArticleOut, 404: Error},
    tags=["Articles"],
)
def get_article_by_slug(
    request: HttpRequest,
    slug: str,
    article_slug: str,
) -> Article | tuple[int, dict[str, str]]:
    user = get_optional_user(request)
    project = resolve_visible_project_or_404(slug, user)
    if isinstance(project, tuple):
        return project
    article = REPO.articles.get_by_project_and_slug(slug, article_slug)
    if article is None or article.project_id != project.id:
        return 404, {"detail": "Article not found"}
    if not article.is_globally_visible and not _can_view_hidden(article, user):
        return 404, {"detail": "Article not found"}
    return article


@router.get(
    "/{slug}/articles/{article_id}",
    response={200: ArticleOut, 401: Error, 403: Error, 404: Error},
    auth=auth,
    tags=["Articles"],
)
def get_article(
    request: HttpRequest,
    slug: str,
    article_id: UUID,
) -> Article | tuple[int, dict[str, str]]:
    project = resolve_visible_project_or_404(slug, request.auth)
    if isinstance(project, tuple):
        return project
    article = _get_article_in_project(project, article_id)
    if isinstance(article, tuple):
        return article
    if not article.is_globally_visible and not _can_view_hidden(article, request.auth):
        return 403, {"detail": "You don't have access to this article"}
    return article


# Domain errors update_article can raise, and how each surfaces to the client.
# A mapping rather than a stack of except arms so adding a case does not push
# the view past ruff's return-statement limit.
_PATCH_ARTICLE_ERRORS: dict[type[ArticleError], tuple[int, str]] = {
    ArticleNotFoundError: (404, "Article not found"),
    ChannelNotFoundError: (404, "Channel not found on this project"),
    ChannelOnWrongProjectError: (404, "Channel not found on this project"),
    ListingImageOnWrongProjectError: (
        422,
        "Listing image must belong to this project",
    ),
    ListingImageNotUploadedError: (
        422,
        "Listing image upload has not completed",
    ),
    InvalidCropError: (422, "Image framing is not a valid crop of this image"),
}


@router.patch(
    "/{slug}/articles/{article_id}",
    response={200: ArticleOut, 401: Error, 403: Error, 404: Error, 422: Error},
    auth=auth,
    tags=["Articles"],
)
def patch_article(
    request: HttpRequest,
    slug: str,
    article_id: UUID,
    payload: ArticleUpdate,
) -> Article | tuple[int, dict[str, str]]:
    project = require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    existing = _get_article_in_project(project, article_id)
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
            listing_image_mode=payload.listing_image_mode,
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
    "/{slug}/articles/{article_id}/publish",
    response={200: ArticleOut, 401: Error, 403: Error, 404: Error, 422: Error},
    auth=auth,
    tags=["Articles"],
)
def publish_article(
    request: HttpRequest,
    slug: str,
    article_id: UUID,
    payload: ArticlePublish,
) -> Article | tuple[int, dict[str, str]]:
    project = require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    existing = _get_article_in_project(project, article_id)
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
    "/{slug}/articles/{article_id}",
    response={204: None, 401: Error, 403: Error, 404: Error},
    auth=auth,
    tags=["Articles"],
)
def delete_article(
    request: HttpRequest,
    slug: str,
    article_id: UUID,
) -> tuple[int, None] | tuple[int, dict[str, str]]:
    project = require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    existing = _get_article_in_project(project, article_id)
    if isinstance(existing, tuple):
        return existing
    HANDLERS.articles.delete_article(article_id)
    return 204, None


# ----------------------------------------------------------------------
# Article images
#
# The rows live on `ProjectImage` so they share the storage and variant
# pipeline, but they are addressed here because they belong to an article.
# Ownership is the same `require_full_edit` + `_get_article_in_project` pair
# the rest of this router uses.
# ----------------------------------------------------------------------


def _get_editable_article(
    slug: str, article_id: UUID, user_id: UUID
) -> Article | tuple[int, dict[str, str]]:
    project = require_full_edit(slug, user_id)
    if isinstance(project, tuple):
        return project
    return _get_article_in_project(project, article_id)


def _get_article_image_or_404(
    article: Article, image_id: UUID, *, status: UploadStatus | None = None
) -> ProjectImage | tuple[int, dict[str, str]]:
    image = REPO.images.get_article_image(article, image_id, status=status)
    if image is None:
        return 404, {"detail": "Image not found"}
    return image


@router.post(
    "/{slug}/articles/{article_id}/images/upload-url",
    response={
        200: PresignedUploadResponse,
        400: Error,
        401: Error,
        403: Error,
        404: Error,
    },
    auth=auth,
    tags=["Article Images"],
)
def get_article_image_upload_url(
    request: HttpRequest,
    slug: str,
    article_id: UUID,
    payload: ArticleImageUploadRequest,
) -> PresignedUploadResponse | tuple[int, dict[str, str]]:
    article = _get_editable_article(slug, article_id, request.auth.id)
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
    "/{slug}/articles/{article_id}/images/{image_id}/complete",
    response={
        200: ProjectImageResponse,
        400: Error,
        401: Error,
        403: Error,
        404: Error,
    },
    auth=auth,
    tags=["Article Images"],
)
def complete_article_image_upload(
    request: HttpRequest,
    slug: str,
    article_id: UUID,
    image_id: UUID,
    payload: ImageUploadCompleteRequest,
) -> ProjectImage | tuple[int, dict[str, str]]:
    article = _get_editable_article(slug, article_id, request.auth.id)
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
    "/{slug}/articles/{article_id}/images/{image_id}",
    response={204: None, 401: Error, 403: Error, 404: Error},
    auth=auth,
    tags=["Article Images"],
)
def delete_article_image(
    request: HttpRequest,
    slug: str,
    article_id: UUID,
    image_id: UUID,
) -> tuple[int, None] | tuple[int, dict[str, str]]:
    article = _get_editable_article(slug, article_id, request.auth.id)
    if isinstance(article, tuple):
        return article

    image = _get_article_image_or_404(article, image_id)
    if isinstance(image, tuple):
        return image

    HANDLERS.images.delete_image(image)
    return 204, None
