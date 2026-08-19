import datetime

from django.db import migrations
from django.utils import timezone


def backfill_winner_announced_at(apps, schema_editor):  # noqa: ARG001
    """Seed the announcement time for competitions decided before the field existed.

    No real timestamp survives — assigning a winner used to record nothing but a
    status change — so the closest honest proxy is the date the competition
    stopped being decidable: voting_end_date, or submission_deadline where
    voting never had its own end date.
    """
    Competition = apps.get_model("projects", "Competition")

    rows = []
    qs = Competition.objects.filter(
        winner__isnull=False, winner_announced_at__isnull=True
    ).only("id", "voting_end_date", "submission_deadline")
    for competition in qs:
        source_date = competition.voting_end_date or competition.submission_deadline
        if source_date is None:
            continue
        competition.winner_announced_at = _as_datetime(source_date)
        rows.append(competition)

    if rows:
        Competition.objects.bulk_update(rows, ["winner_announced_at"])


def _as_datetime(value: datetime.date) -> datetime.datetime:
    naive = datetime.datetime.combine(value, datetime.time.min)
    if timezone.is_naive(naive):
        return timezone.make_aware(naive, timezone.get_default_timezone())
    return naive


def noop(apps, schema_editor):  # noqa: ARG001
    # Reversing leaves the values in place; the field drop removes them.
    return


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0051_competition_winner_announced_at"),
    ]

    operations = [
        migrations.RunPython(backfill_winner_announced_at, noop),
    ]
