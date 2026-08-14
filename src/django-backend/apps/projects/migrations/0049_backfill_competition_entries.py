from datetime import datetime, time

from django.db import migrations
from django.utils import timezone


def _start_of_day(day):
    """`Competition.start_date` is a date; `entered_at` is a datetime."""
    return timezone.make_aware(datetime.combine(day, time.min))


def backfill_entries(apps, schema_editor):
    """Copy the auto-created M2M rows into `competition_entries`.

    Runs before 0050 swaps the relation onto the through model, which drops the
    auto-created table. Idempotent via get_or_create on the unique pair, so a
    partial run can be repeated.
    """
    Competition = apps.get_model("projects", "Competition")
    CompetitionEntry = apps.get_model("projects", "CompetitionEntry")

    for competition in Competition.objects.all().iterator():
        for project in competition.projects.all().iterator():
            CompetitionEntry.objects.get_or_create(
                competition=competition,
                project=project,
                defaults={
                    # The best timestamp available: entry used to happen at
                    # publish, so published_at is the real moment. Competitions
                    # populated by hand have projects with no published_at.
                    "entered_at": project.published_at
                    or _start_of_day(competition.start_date),
                    "entered_via": "backfill",
                    "entered_by": None,
                },
            )


def remove_backfilled_entries(apps, schema_editor):
    """Only the rows this migration wrote — entries created since through the
    endpoint or the admin are not ours to delete."""
    CompetitionEntry = apps.get_model("projects", "CompetitionEntry")
    CompetitionEntry.objects.filter(entered_via="backfill").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0048_competitionentry"),
    ]

    operations = [
        migrations.RunPython(backfill_entries, remove_backfilled_entries),
    ]
