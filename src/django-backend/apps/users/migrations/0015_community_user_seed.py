from django.contrib.auth.hashers import make_password
from django.db import migrations

from apps.users.seed import (
    COMMUNITY_USER_EMAIL,
    COMMUNITY_USER_ID,
    COMMUNITY_USER_INFO,
    COMMUNITY_USER_KENNITALA,
)


def create_community_user(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.get_or_create(
        id=COMMUNITY_USER_ID,
        defaults={
            "email": COMMUNITY_USER_EMAIL,
            "kennitala": COMMUNITY_USER_KENNITALA,
            "is_system_user": True,
            "is_active": True,
            "is_verified": True,
            "info": COMMUNITY_USER_INFO,
            # `make_password(None)` produces Django's "unusable password" sentinel.
            "password": make_password(None),
        },
    )


def delete_community_user(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(id=COMMUNITY_USER_ID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0014_user_is_system_user"),
    ]

    operations = [
        migrations.RunPython(create_community_user, delete_community_user),
    ]
