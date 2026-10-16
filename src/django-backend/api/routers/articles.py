"""Article routes that live under a project: create, list, read by slug.

Everything addressed by article id — read for editing, patch, publish,
delete, images — is in `article_items.py` at `/api/articles/{id}`, where
authorisation comes from the article rather than the slug in the URL.
"""

from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.routers._helpers import (
    get_optional_user,
    require_full_edit,
    resolve_visible_project_or_404,
)
from api.schemas.article import ArticleCreate, ArticleListItem, ArticleOut
from api.schemas.errors import Error
from apps.articles.models import Article
from apps.users.models import User
from services import HANDLERS, REPO
from services.articles.exceptions import (
    ChannelNotFoundError,
    ChannelOnWrongProjectError,
)

router = Router()


def can_view_hidden(article: Article, user: User | None) -> bool:
    """Who may read an article the site is not showing globally.

    Authorisation, deliberately separate from `Article.is_globally_visible`:
    that answers "does this render for everyone", this answers "may this user
    see it anyway". Covers drafts, articles awaiting admin review and demoted
    articles alike — an author keeps access to their own work in edit mode
    whatever the site has decided about it. Shared with the author-owned
    by-slug read in `users.py`.
    """
    if user is None:
        return False
    if article.author_id == user.id:
        return True
    if article.project_id is None:
        return False
    return REPO.project.user_can_edit(article.project_id, user.id)


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
    if not article.is_globally_visible and not can_view_hidden(article, user):
        return 404, {"detail": "Article not found"}
    return article
