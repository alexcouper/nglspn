from __future__ import annotations

from typing import TYPE_CHECKING

from api.auth.jwt import get_user_from_token
from apps.projects.models import ProjectStatus
from services import REPO
from services.project.exceptions import ProjectNotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from django.http import HttpRequest

    from apps.articles.models import Article
    from apps.projects.models import Project
    from apps.users.models import User


def get_optional_user(request: HttpRequest) -> User | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return get_user_from_token(auth_header[7:])
    return None


def resolve_project_or_404(
    slug: str,
) -> Project | tuple[int, dict[str, str]]:
    try:
        return REPO.project.get_by_identifier(slug)
    except ProjectNotFoundError:
        return 404, {"detail": "Project not found"}


def require_full_edit(slug: str, user_id: UUID) -> Project | tuple[int, dict[str, str]]:
    resolved = resolve_project_or_404(slug)
    if isinstance(resolved, tuple):
        return resolved
    if not REPO.project.user_can_edit(resolved.id, user_id):
        return 403, {"detail": "You don't have edit access to this project"}
    return resolved


def resolve_visible_project_or_404(
    slug: str, user: User | None
) -> Project | tuple[int, dict[str, str]]:
    resolved = resolve_project_or_404(slug)
    if isinstance(resolved, tuple):
        return resolved
    if resolved.status == ProjectStatus.APPROVED:
        return resolved
    if user is not None and user.is_superuser:
        return resolved
    if user is not None and REPO.project.user_can_edit(resolved.id, user.id):
        return resolved
    return 404, {"detail": "Project not found"}


def can_edit_article(article: Article, user_id: UUID) -> bool:
    """Who may change an article: its author for an author-owned one, any
    `full_edit` contributor for one on a project.

    Derived from the article rather than from a project in the URL, so the
    id-addressed routes need no slug and the two kinds share one rule.
    """
    if article.project_id is None:
        return article.author_id == user_id
    return REPO.project.user_can_edit(article.project_id, user_id)


def resolve_editable_article_or_404(
    article_id: UUID, user_id: UUID
) -> Article | tuple[int, dict[str, str]]:
    """The article, if `user_id` may edit it; otherwise 404.

    404 rather than 403 for a caller without rights, so an article id reveals
    nothing about whether it exists.
    """
    article = REPO.articles.get_by_id(article_id)
    if article is None or not can_edit_article(article, user_id):
        return 404, {"detail": "Article not found"}
    return article
