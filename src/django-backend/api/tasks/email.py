from __future__ import annotations

from uuid import UUID

from django.conf import settings
from django_tasks import task

from apps.emails.models import BroadcastEmail, BroadcastEmailStatus
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
    from services import HANDLERS, REPO  # noqa: PLC0415

    project = Project.objects.get(id=UUID(project_id))
    for contributor in REPO.project.list_notifiable_contributors(UUID(project_id)):
        HANDLERS.email.send_project_approved_email(project, contributor.user)


@task()
def send_new_project_notification(project_id: str) -> None:
    recipient = settings.NEW_PROJECT_NOTIFICATION_EMAIL
    if not recipient:
        return

    from services import HANDLERS  # noqa: PLC0415

    project = Project.objects.select_related("creator").get(id=UUID(project_id))
    HANDLERS.email.send_new_project_notification(project, recipient)


@task()
def send_broadcast_email(broadcast_id: str, sent_by_user_id: str) -> None:
    from services import HANDLERS  # noqa: PLC0415

    broadcast = BroadcastEmail.objects.get(id=UUID(broadcast_id))

    if broadcast.status != BroadcastEmailStatus.QUEUED_FOR_SENDING:
        return

    sent_by = User.objects.get(id=UUID(sent_by_user_id))
    HANDLERS.email.send_broadcast(broadcast, sent_by)
