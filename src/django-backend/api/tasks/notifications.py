from __future__ import annotations

import logging
from uuid import UUID

from django_tasks import task

logger = logging.getLogger(__name__)


@task()
def create_discussion_notifications(discussion_id: str) -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.notifications.create_notifications_for_discussion(UUID(discussion_id))


# Per-kind digest tasks. Nothing in this repo enqueues them: the schedule is a
# set of Kubernetes CronJobs in the naglasupan-hq infra repo
# (`k8s/base/notifications/`), each running
# `manage.py enqueue_digest --kind <kind> --cadence <cadence>` against this
# image. Renaming a task here therefore only breaks production if the matching
# CLI arguments change — see `apps/notifications/management/commands/enqueue_digest.py`,
# which is the seam that keeps the cron off these symbol names.
#
# Deployed wall-clock (UTC), mirrored from the CronJobs:
#   - discussion hourly: :05 past the hour
#   - article hourly   : :05 past the hour
#   - discussion daily : 18:00
#   - article daily    : 18:00
#   - article weekly   : Monday 18:00
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
