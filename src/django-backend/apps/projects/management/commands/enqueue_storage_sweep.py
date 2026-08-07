"""Enqueue the orphaned-storage sweep. Called by `storage-sweep-daily`.

Same rationale as `enqueue_digest` / `enqueue_notification_cleanup`: the cron
names a CLI, not a Python symbol, so renaming the task does not break the
deployed schedule.
"""

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "Enqueue the task that deletes storage objects no row owns any more."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Maximum tombstones and abandoned uploads to process per run.",
        )

    def handle(self, *args, **options) -> None:
        from api.tasks.images import sweep_orphaned_storage_objects  # noqa: PLC0415

        batch_size = options["batch_size"]
        sweep_orphaned_storage_objects.enqueue(batch_size=batch_size)

        self.stdout.write(
            self.style.SUCCESS(
                f"Enqueued sweep_orphaned_storage_objects (batch_size={batch_size})"
            )
        )
