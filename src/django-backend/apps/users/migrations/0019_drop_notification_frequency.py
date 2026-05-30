from django.db import migrations


class Migration(migrations.Migration):
    """Drop the legacy `notification_frequency` column from users.

    Depends on:
      - 0018 (the new discussion / article cadence columns exist and have
        been populated from this column via RunPython).
      - The code flip — every reader of `notification_frequency` is gone by
        the time this migration ships.
    """

    dependencies = [
        ("users", "0018_user_article_email_frequency_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="notification_frequency",
        ),
    ]
