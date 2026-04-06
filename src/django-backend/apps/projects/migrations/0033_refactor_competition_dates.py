from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0032_add_voting_status"),
    ]

    operations = [
        migrations.RenameField(
            model_name="competition",
            old_name="end_date",
            new_name="submission_deadline",
        ),
        migrations.AddField(
            model_name="competition",
            name="voting_end_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
