from django.db import migrations


class Migration(migrations.Migration):
    """Drop the legacy `email_enabled` and `in_app_enabled` columns.

    Depends on:
      - 0003 (model renamed so the FollowedChannel state matches the table)
      - 0004 (both-off rows swept; surviving rows are all "I follow this")
    Also depends on the code flip — every reader of these columns is gone
    by the time this migration ships.
    """

    dependencies = [
        ("follows", "0004_sweep_both_off_rows"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="followedchannel",
            name="email_enabled",
        ),
        migrations.RemoveField(
            model_name="followedchannel",
            name="in_app_enabled",
        ),
    ]
