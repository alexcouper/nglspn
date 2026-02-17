from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_emailverificationcode"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="opt_in_to_external_promotions",
            field=models.BooleanField(default=True),
        ),
    ]
