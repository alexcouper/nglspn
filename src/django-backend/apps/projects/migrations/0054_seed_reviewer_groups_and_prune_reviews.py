from django.db import migrations
from django.db.models import Exists, OuterRef

EVERYONE = "Everyone"
IN_PROGRESS = "in_progress"
COMPLETED = "completed"
ENDED = "ended"


def seed_everyone_and_backfill(apps, schema_editor):  # noqa: ARG001
    ReviewerGroup = apps.get_model("projects", "ReviewerGroup")
    Competition = apps.get_model("projects", "Competition")

    everyone, _ = ReviewerGroup.objects.get_or_create(
        name=EVERYONE, defaults={"includes_all_users": True}
    )
    Competition.objects.filter(reviewer_group__isnull=True).update(
        reviewer_group=everyone
    )


def prune_assignment_only_reviews(apps, schema_editor):  # noqa: ARG001
    """Drop the rows that only ever meant "was assigned".

    Review access is now derived from the competition, so a row has to mean a
    review was started. A row that is not completed and ranks nothing never
    was one. Neither it nor an `ended` row was counted by the tally, so no
    result moves. `ended` is now derived from the competition's status, so the
    rows that survive with it go back to `in_progress`.
    """
    CompetitionReviewer = apps.get_model("projects", "CompetitionReviewer")
    ProjectRanking = apps.get_model("projects", "ProjectRanking")

    has_rankings = ProjectRanking.objects.filter(
        reviewer_id=OuterRef("user_id"),
        competition_id=OuterRef("competition_id"),
    )
    CompetitionReviewer.objects.exclude(status=COMPLETED).exclude(
        Exists(has_rankings)
    ).delete()
    CompetitionReviewer.objects.filter(status=ENDED).update(status=IN_PROGRESS)


def noop(apps, schema_editor):  # noqa: ARG001
    # Deleted rows are not recoverable; reversing only lets the schema roll back.
    return


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0053_reviewer_group"),
    ]

    operations = [
        migrations.RunPython(seed_everyone_and_backfill, noop),
        migrations.RunPython(prune_assignment_only_reviews, noop),
    ]
