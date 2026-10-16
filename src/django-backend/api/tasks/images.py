from __future__ import annotations

import logging

from django_tasks import task

logger = logging.getLogger(__name__)


@task()
def generate_image_variants(image_id: str) -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.images.generate_variants(image_id)


# Nothing in this repo enqueues this: the schedule is a Kubernetes CronJob in
# the naglasupan-hq infra repo running
# `manage.py enqueue_storage_sweep` against this image, same seam as the digest
# CronJobs — the cron names a CLI, not a Python symbol. Until that CronJob
# exists the tombstone table grows one row per deleted image forever, and
# nothing in this repo will tell you.
@task()
def sweep_orphaned_storage_objects(batch_size: int = 500) -> None:
    from services import HANDLERS  # noqa: PLC0415

    result = HANDLERS.images.sweep_orphaned_objects(batch_size=batch_size)
    logger.info(
        "sweep_orphaned_storage_objects: reaped=%d deleted=%d failures=%d",
        result.pending_uploads_reaped,
        result.objects_deleted,
        result.failures,
    )
