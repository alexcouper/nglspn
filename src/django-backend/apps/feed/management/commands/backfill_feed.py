"""Seed the Latest feed from history that predates the stream.

Articles are deliberately out of scope: they enter the feed through the publish
path, and at the time this shipped none had been published. Widening the scope
later is safe — every append is idempotent, so a re-run adds only what is
missing.

The command doubles as a reconciler. Competition milestones are date-driven, and
nothing fires when a date simply passes, so re-running picks up competitions
that have opened or closed since the last run.
"""

from typing import Any

from django.core.management.base import BaseCommand

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
        counts = {"projects": 0, "competitions": 0}

        for project in Project.objects.filter(status=ProjectStatus.APPROVED).iterator():
            if dry_run:
                counts["projects"] += 1
                continue
            if HANDLERS.feed.append_project_published(project) is not None:
                counts["projects"] += 1

        for competition in Competition.objects.iterator():
            if dry_run:
                counts["competitions"] += 1
                continue
            appended = [
                HANDLERS.feed.append_competition_opened(competition),
                HANDLERS.feed.append_competition_closed(competition),
                HANDLERS.feed.append_competition_winner(competition),
            ]
            counts["competitions"] += sum(1 for event in appended if event is not None)

        prefix = "would append" if dry_run else "covered"
        self.stdout.write(
            f"backfill_feed: {prefix} {counts['projects']} project entries, "
            f"{counts['competitions']} competition entries"
        )
