from __future__ import annotations

from typing import TYPE_CHECKING

from api.auth.jwt import get_user_from_token
from apps.projects.models import ProjectStatus
from services import REPO
from services.project.exceptions import ProjectNotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from django.http import HttpRequest

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
