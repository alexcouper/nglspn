from __future__ import annotations

import logging
from uuid import UUID

from django_tasks import task

logger = logging.getLogger(__name__)


@task()
def create_discussion_notifications(discussion_id: str) -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.notifications.create_notifications_for_discussion(UUID(discussion_id))


# Per-kind digest tasks. Schedules are wired in the deployment cron / cloud
# scheduler — wall-clock targets agreed for the first rollout:
#   - discussion hourly: every hour at :00
#   - discussion daily : 09:00 UTC
#   - article hourly   : every hour at :05 (offset from discussion to spread load)
#   - article daily    : 09:00 UTC
#   - article weekly   : Monday 09:00 UTC
@task()
def send_discussion_digest_hourly() -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.notifications.send_discussion_digest("hourly")


@task()
def send_discussion_digest_daily() -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.notifications.send_discussion_digest("daily")


@task()
def send_article_digest_hourly() -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.notifications.send_article_digest("hourly")


@task()
def send_article_digest_daily() -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.notifications.send_article_digest("daily")


@task()
def send_article_digest_weekly() -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.notifications.send_article_digest("weekly")


@task()
def delete_old_read_notifications() -> None:
    from services import HANDLERS  # noqa: PLC0415

    deleted = HANDLERS.notifications.delete_old_read_notifications()
    logger.info("delete_old_read_notifications removed %d rows", deleted)
