from django.db import migrations


def set_notification_immediate(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.all().update(notification_frequency="hourly")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0011_set_existing_users_notification_never"),
    ]

    operations = [
        migrations.RunPython(set_notification_immediate, migrations.RunPython.noop),
    ]
