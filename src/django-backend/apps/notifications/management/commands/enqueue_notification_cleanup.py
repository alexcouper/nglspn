"""Enqueue the read-notification cleanup task. Called by `notify-cleanup-daily`.

Same rationale as `enqueue_digest`: the cron names a CLI, not a Python symbol.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Enqueue the task that deletes old read notifications."

    def handle(self, *args, **options) -> None:
        from api.tasks.notifications import (  # noqa: PLC0415
            delete_old_read_notifications,
        )

        delete_old_read_notifications.enqueue()

        self.stdout.write(self.style.SUCCESS("Enqueued delete_old_read_notifications"))
