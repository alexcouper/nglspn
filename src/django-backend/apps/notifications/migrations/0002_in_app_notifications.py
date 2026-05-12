from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="notification",
            old_name="cadence",
            new_name="email_cadence",
        ),
        migrations.RenameField(
            model_name="notification",
            old_name="sent",
            new_name="email_sent",
        ),
        migrations.RenameField(
            model_name="notification",
            old_name="sent_at",
            new_name="email_sent_at",
        ),
        migrations.AddField(
            model_name="notification",
            name="in_app_read_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["recipient", "in_app_read_at"],
                name="notifications_recip_inapp_idx",
            ),
        ),
    ]
