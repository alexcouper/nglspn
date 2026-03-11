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


@task()
def send_broadcast_email(broadcast_id: str, sent_by_user_id: str) -> None:
    from django.utils import timezone  # noqa: PLC0415

    from apps.emails.models import BroadcastEmail, BroadcastEmailStatus  # noqa: PLC0415
    from services import HANDLERS  # noqa: PLC0415

    broadcast = BroadcastEmail.objects.get(id=UUID(broadcast_id))

    if broadcast.status != BroadcastEmailStatus.QUEUED_FOR_SENDING:
        return

    broadcast.status = BroadcastEmailStatus.SENDING
    broadcast.save(update_fields=["status"])

    try:
        HANDLERS.email.send_broadcast(broadcast)
    except Exception:
        broadcast.status = BroadcastEmailStatus.FAILED
        broadcast.save(update_fields=["status"])
        raise

    broadcast.status = BroadcastEmailStatus.SENT
    broadcast.sent_at = timezone.now()
    broadcast.sent_by = User.objects.get(id=UUID(sent_by_user_id))
    broadcast.save(update_fields=["status", "sent_at", "sent_by"])
