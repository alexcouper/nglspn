"""Seed the Latest feed from history that predates the stream.

Articles are deliberately out of scope: they enter the feed through the publish
path, and at the time this shipped none had been published. Widening the scope
later is safe — every append is idempotent, so a re-run adds only what is
missing.

Competition milestones need no reconciling here. They are appended as soon as
their date is known and held out of the feed by `renderable()` until it
arrives, so nothing has to run when a date passes. What this command covers is
the competitions that already existed when the stream shipped and have not been
saved since.
"""

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.feed.models import FeedEvent
from apps.projects.models import Competition, Project, ProjectStatus
from services import HANDLERS


class Command(BaseCommand):
    help = "Append feed events for projects, tipoffs and competitions."

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
            counts = self._append_everything()
            if dry_run:
                transaction.set_rollback(True)

        prefix = "would append" if dry_run else "appended"
        self.stdout.write(
            f"backfill_feed: {prefix} {counts['projects']} project entries, "
            f"{counts['competitions']} competition entries"
        )

    @staticmethod
    def _append_everything() -> dict[str, int]:
        # Counted by how far the stream grew, not by how many appenders
        # returned a row: they return the existing entry when there is one, so
        # a re-run would otherwise report the whole site as freshly appended.
        start = FeedEvent.objects.count()

        for project in Project.objects.filter(status=ProjectStatus.APPROVED).iterator():
            HANDLERS.feed.append_project_published(project)
        after_projects = FeedEvent.objects.count()

        for competition in Competition.objects.iterator():
            HANDLERS.feed.append_competition_opened(competition)
            HANDLERS.feed.append_competition_closed(competition)
            HANDLERS.feed.append_competition_winner(competition)

        return {
            "projects": after_projects - start,
            "competitions": FeedEvent.objects.count() - after_projects,
        }
