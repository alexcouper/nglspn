from django.db import migrations


def backfill_voting_end_date(apps, schema_editor):
    from django.db.models import F

    Competition = apps.get_model("projects", "Competition")
    Competition.objects.filter(voting_end_date__isnull=True).update(
        voting_end_date=F("submission_deadline")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0033_refactor_competition_dates"),
    ]

    operations = [
        migrations.RunPython(
            backfill_voting_end_date,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
