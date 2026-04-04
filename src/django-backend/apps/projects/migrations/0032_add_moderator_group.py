from django.db import migrations

MODERATOR_GROUP_NAME = "MODERATOR"


def create_moderator_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=MODERATOR_GROUP_NAME)


def remove_moderator_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=MODERATOR_GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0031_remove_purpose_field"),
    ]

    operations = [
        migrations.RunPython(create_moderator_group, remove_moderator_group),
    ]
