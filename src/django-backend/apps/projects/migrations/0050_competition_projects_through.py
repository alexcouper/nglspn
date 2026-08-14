from django.db import migrations, models


def _noop(apps, schema_editor):
    """Forward direction: 0049 already copied the rows across."""


def _restore_join_table(apps, schema_editor):
    """Reverse direction: put the rows back in the re-created join table.

    Without this, rolling back drops every project's competition membership —
    the entries survive in `competition_entries` only until 0049 reverses and
    deletes them.
    """
    Competition = apps.get_model("projects", "Competition")
    CompetitionEntry = apps.get_model("projects", "CompetitionEntry")

    by_competition: dict = {}
    for entry in CompetitionEntry.objects.all().iterator():
        by_competition.setdefault(entry.competition_id, []).append(entry.project_id)

    for competition in Competition.objects.filter(id__in=by_competition):
        competition.projects.add(*by_competition[competition.id])


class Migration(migrations.Migration):
    """Point `Competition.projects` at the entry model.

    `AlterField` is what the autodetector generates and what the schema editor
    refuses — Django cannot add `through=` to a live M2M. So the two halves are
    done separately: the database drops the auto-created join table (its rows
    were copied into `competition_entries` by 0049), and the state is told the
    relation now runs through `CompetitionEntry`.
    """

    dependencies = [
        ("projects", "0049_backfill_competition_entries"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # Ordering matters on the way back: reversing runs this list
                # backwards, so RemoveField re-creates the join table before
                # _restore_join_table refills it.
                migrations.RunPython(_noop, _restore_join_table),
                migrations.RemoveField(
                    model_name="competition",
                    name="projects",
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name="competition",
                    name="projects",
                ),
                migrations.AddField(
                    model_name="competition",
                    name="projects",
                    field=models.ManyToManyField(
                        blank=True,
                        related_name="competitions",
                        through="projects.CompetitionEntry",
                        to="projects.project",
                    ),
                ),
            ],
        ),
    ]
