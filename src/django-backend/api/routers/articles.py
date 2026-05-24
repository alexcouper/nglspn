from uuid import UUID

from django.http import HttpRequest
from ninja import Router

from api.auth.jwt import get_user_from_token
from api.auth.security import auth
from api.schemas.article import (
    ArticleCreate,
    ArticleListItem,
    ArticleOut,
    ArticlePublish,
    ArticleUpdate,
)
from api.schemas.errors import Error
from apps.articles.models import Article, ArticleState
from apps.projects.models import Project
from apps.users.models import User
from services import HANDLERS, REPO
from services.articles.exceptions import (
    ArticleNotFoundError,
    ArticleNotPublishableError,
    ChannelNotFoundError,
    ChannelOnWrongProjectError,
    HeroImageOnWrongProjectError,
)
from services.project.exceptions import ProjectNotFoundError

router = Router()


def _get_optional_user(request: HttpRequest) -> User | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return get_user_from_token(auth_header[7:])
    return None


def _can_view_draft(article: Article, user: User | None) -> bool:
    if user is None:
        return False
    if article.author_id == user.id:
        return True
    return REPO.project.user_can_edit(article.project_id, user.id)


def _resolve_project_or_404(
    slug: str,
) -> Project | tuple[int, dict[str, str]]:
    try:
        return REPO.project.get_by_identifier(slug)
    except ProjectNotFoundError:
        return 404, {"detail": "Project not found"}


def _require_full_edit(
    slug: str, user_id: UUID
) -> Project | tuple[int, dict[str, str]]:
    resolved = _resolve_project_or_404(slug)
    if isinstance(resolved, tuple):
        return resolved
    if not REPO.project.user_can_edit(resolved.id, user_id):
        return 403, {"detail": "You don't have edit access to this project"}
    return resolved


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
    project = _require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    try:
        article = HANDLERS.articles.create_draft(
            project_id=project.id,
            channel_id=payload.channel_id,
            author_id=request.auth.id,
            title=payload.title,
            body=payload.body,
            hero_image_id=payload.hero_image_id,
        )
    except (ChannelNotFoundError, ChannelOnWrongProjectError):
        return 404, {"detail": "Channel not found on this project"}
    except HeroImageOnWrongProjectError:
        return 422, {"detail": "Hero image must belong to this project"}
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
    project = _resolve_project_or_404(slug)
    if isinstance(project, tuple):
        return project
    user = _get_optional_user(request)
    include_drafts = user is not None and REPO.project.user_can_edit(
        project.id, user.id
    )
    return list(REPO.articles.for_project(project.id, include_drafts=include_drafts))


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
    article = REPO.articles.get_by_project_and_slug(slug, article_slug)
    if article is None:
        return 404, {"detail": "Article not found"}
    if article.state != ArticleState.PUBLISHED:
        user = _get_optional_user(request)
        if not _can_view_draft(article, user):
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
    project = _resolve_project_or_404(slug)
    if isinstance(project, tuple):
        return project
    article = REPO.articles.get_by_id(article_id)
    if article is None or article.project_id != project.id:
        return 404, {"detail": "Article not found"}
    if article.state != ArticleState.PUBLISHED and not _can_view_draft(
        article, request.auth
    ):
        return 403, {"detail": "You don't have access to this draft"}
    return article


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
    project = _require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    existing = REPO.articles.get_by_id(article_id)
    if existing is None or existing.project_id != project.id:
        return 404, {"detail": "Article not found"}
    try:
        article = HANDLERS.articles.update_article(
            article_id,
            title=payload.title,
            body=payload.body,
            hero_image_id=payload.hero_image_id,
            channel_id=payload.channel_id,
            published_at=payload.published_at,
        )
    except ArticleNotFoundError:
        return 404, {"detail": "Article not found"}
    except (ChannelNotFoundError, ChannelOnWrongProjectError):
        return 404, {"detail": "Channel not found on this project"}
    except HeroImageOnWrongProjectError:
        return 422, {"detail": "Hero image must belong to this project"}
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
    project = _require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    existing = REPO.articles.get_by_id(article_id)
    if existing is None or existing.project_id != project.id:
        return 404, {"detail": "Article not found"}
    try:
        article = HANDLERS.articles.publish(
            article_id, published_at=payload.published_at
        )
    except ArticleNotFoundError:
        return 404, {"detail": "Article not found"}
    except ArticleNotPublishableError:
        return 422, {"detail": "Article requires title, body and hero image to publish"}
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
    project = _require_full_edit(slug, request.auth.id)
    if isinstance(project, tuple):
        return project
    existing = REPO.articles.get_by_id(article_id)
    if existing is None or existing.project_id != project.id:
        return 404, {"detail": "Article not found"}
    HANDLERS.articles.delete_article(article_id)
    return 204, None
