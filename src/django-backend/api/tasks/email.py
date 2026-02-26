from __future__ import annotations

from uuid import UUID

from django_tasks import task

from apps.projects.models import Project
from apps.users.models import User


@task()
def send_verification_email(user_id: str, code: str, expires_minutes: int) -> None:
    from services import HANDLERS  # noqa: PLC0415

    user = User.objects.get(id=UUID(user_id))
    HANDLERS.email.send_verification_email(user, code, expires_minutes)


@task()
def send_password_reset_email(user_id: str, code: str, expires_minutes: int) -> None:
    from services import HANDLERS  # noqa: PLC0415

    user = User.objects.get(id=UUID(user_id))
    HANDLERS.email.send_password_reset_email(user, code, expires_minutes)


@task()
def send_project_approved_email(project_id: str) -> None:
    from services import HANDLERS  # noqa: PLC0415

    project = Project.objects.select_related("owner").get(id=UUID(project_id))
    HANDLERS.email.send_project_approved_email(project)
