from __future__ import annotations

from uuid import UUID

from django_tasks import task

from apps.projects.models import Project
from apps.users.models import User
from services import HANDLERS


@task()
def send_verification_email(user_id: str, code: str, expires_minutes: int) -> None:
    user = User.objects.get(id=UUID(user_id))
    HANDLERS.email.send_verification_email(user, code, expires_minutes)


@task()
def send_project_approved_email(project_id: str) -> None:
    project = Project.objects.select_related("owner").get(id=UUID(project_id))
    HANDLERS.email.send_project_approved_email(project)
