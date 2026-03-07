from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0003_sentemail"),
    ]

    operations = [
        migrations.AddField(
            model_name="sentemail",
            name="html_body",
            field=models.TextField(blank=True, default=""),
        ),
    ]
