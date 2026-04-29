from __future__ import annotations

from typing import TYPE_CHECKING

from apps.projects.models import ProjectContributor

if TYPE_CHECKING:
    from uuid import UUID

    from apps.projects.models import Project
    from apps.users.models import User


def user_can_edit_project(project: Project, user: User | None) -> bool:
    """Return True iff `user` has a contributor row on `project` granting full edit."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return user_id_can_edit_project(project, user.id)


def user_id_can_edit_project(project: Project, user_id: UUID | None) -> bool:
    """Same as user_can_edit_project, but for the user's id (no auth check)."""
    if user_id is None:
        return False
    return ProjectContributor.objects.filter(
        project=project,
        user_id=user_id,
        full_edit=True,
    ).exists()
