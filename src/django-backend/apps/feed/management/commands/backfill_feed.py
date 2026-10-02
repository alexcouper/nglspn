"""Seed the Latest feed from history that predates the stream.

Articles are deliberately out of scope: they enter the feed through the publish
path, and at the time this shipped none had been published. Widening the scope
later is safe — every append is idempotent, so a re-run adds only what is
missing.
"""

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.feed.models import FeedEvent
from apps.projects.models import Project, ProjectStatus
from services import HANDLERS


class Command(BaseCommand):
    help = "Append feed events for projects and tipoffs."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be appended without writing.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options["dry_run"]

        # A dry run appends for real and rolls the transaction back. Counting
        # candidates instead would report every project on every re-run, when
        # the appenders are idempotent and the honest answer is usually zero.
        with transaction.atomic():
            appended = self._append_everything()
            if dry_run:
                transaction.set_rollback(True)

        prefix = "would append" if dry_run else "appended"
        self.stdout.write(f"backfill_feed: {prefix} {appended} project entries")

    @staticmethod
    def _append_everything() -> int:
        # Counted by how far the stream grew, not by how many appenders
        # returned a row: they return the existing entry when there is one, so
        # a re-run would otherwise report the whole site as freshly appended.
        start = FeedEvent.objects.count()

        for project in Project.objects.filter(status=ProjectStatus.APPROVED).iterator():
            HANDLERS.feed.append_project_published(project)

        return FeedEvent.objects.count() - start
