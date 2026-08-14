import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create the entry model. `Competition.projects` is swapped onto it in
    0050, after 0049 has copied the existing rows across."""

    dependencies = [
        ("projects", "0047_competition_entry_series"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CompetitionEntry",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("entered_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "entered_via",
                    models.CharField(
                        choices=[
                            ("manual", "Entered by contributor"),
                            ("admin", "Added by admin"),
                            ("backfill", "Backfilled"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "competition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="projects.competition",
                    ),
                ),
                (
                    "entered_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="competition_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="competition_entries",
                        to="projects.project",
                    ),
                ),
            ],
            options={
                "db_table": "competition_entries",
                "ordering": ["-entered_at"],
                "unique_together": {("competition", "project")},
            },
        ),
    ]
