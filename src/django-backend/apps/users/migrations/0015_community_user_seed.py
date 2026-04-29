from uuid import UUID

from django.contrib.auth.hashers import make_password
from django.db import migrations

# Frozen-in-time copies of the seed-user identity. Mirrors `apps/users/seed.py`
# at the time this migration was authored. Do NOT replace with imports — past
# migrations must be deterministic against future edits to seed.py.
_COMMUNITY_USER_ID = UUID("77777777-7777-7777-7777-777777777777")
_COMMUNITY_USER_KENNITALA = "7777777777"
_COMMUNITY_USER_EMAIL = "community@naglasupan.is"
_COMMUNITY_USER_INFO = (
    "Projects submitted by community members but owned by people outside of Naglasúpan."
)


def create_community_user(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.get_or_create(
        id=_COMMUNITY_USER_ID,
        defaults={
            "email": _COMMUNITY_USER_EMAIL,
            "kennitala": _COMMUNITY_USER_KENNITALA,
            "is_system_user": True,
            "is_active": True,
            "is_verified": True,
            "info": _COMMUNITY_USER_INFO,
            # `make_password(None)` produces Django's "unusable password" sentinel.
            "password": make_password(None),
        },
    )


def delete_community_user(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(id=_COMMUNITY_USER_ID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0014_user_is_system_user"),
    ]

    operations = [
        migrations.RunPython(create_community_user, delete_community_user),
    ]
