from __future__ import annotations

import logging
from uuid import UUID

from django_tasks import task

logger = logging.getLogger(__name__)


@task()
def create_discussion_notifications(discussion_id: str) -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.notifications.create_notifications_for_discussion(UUID(discussion_id))


@task()
def send_hourly_notifications() -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.notifications.send_batch_notifications("hourly")


@task()
def send_daily_notifications() -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.notifications.send_batch_notifications("daily")


@task()
def delete_old_read_notifications() -> None:
    from services import HANDLERS  # noqa: PLC0415

    deleted = HANDLERS.notifications.delete_old_read_notifications()
    logger.info("delete_old_read_notifications removed %d rows", deleted)
