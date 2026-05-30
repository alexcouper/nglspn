from django.db import migrations, models


def copy_notification_frequency_to_discussion(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.all().update(
        discussion_email_frequency=models.F("notification_frequency")
    )


def reverse_copy(apps, schema_editor):
    # Drop only the new field's contents; original column is untouched.
    User = apps.get_model("users", "User")
    User.objects.all().update(discussion_email_frequency="hourly")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0017_drop_email_opt_in_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="article_email_frequency",
            field=models.CharField(
                choices=[
                    ("hourly", "At most every hour"),
                    ("daily", "At most every day"),
                    ("weekly", "At most every week"),
                    ("never", "Never"),
                ],
                default="hourly",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="discussion_email_frequency",
            field=models.CharField(
                choices=[
                    ("immediate", "Every Time"),
                    ("hourly", "At most every hour"),
                    ("daily", "At most every day"),
                    ("never", "Never"),
                ],
                default="hourly",
                max_length=20,
            ),
        ),
        migrations.RunPython(
            copy_notification_frequency_to_discussion,
            reverse_code=reverse_copy,
        ),
        migrations.AlterField(
            model_name="user",
            name="notification_frequency",
            field=models.CharField(
                choices=[
                    ("immediate", "Every Time"),
                    ("hourly", "At most every hour"),
                    ("daily", "At most every day"),
                    ("weekly", "At most every week"),
                    ("never", "Never"),
                ],
                default="hourly",
                max_length=20,
            ),
        ),
    ]
