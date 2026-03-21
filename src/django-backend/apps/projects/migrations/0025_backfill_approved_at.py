from django.db import migrations, models


def backfill_approved_at(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Project.objects.filter(status="approved", approved_at__isnull=True).update(
        approved_at=models.F("created_at")
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0024_projectcategory_project_is_featured_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_approved_at, noop),
    ]
