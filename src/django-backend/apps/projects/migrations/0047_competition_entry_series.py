from django.db import migrations, models


class Migration(migrations.Migration):
    """Group competitions into series.

    Every competition that exists when this runs is part of the recurring
    monthly round, which is exactly what the field default says.
    """

    dependencies = [
        ("projects", "0046_orphanedstorageobject"),
    ]

    operations = [
        migrations.AddField(
            model_name="competition",
            name="entry_series",
            field=models.SlugField(default="monthly"),
        ),
    ]
