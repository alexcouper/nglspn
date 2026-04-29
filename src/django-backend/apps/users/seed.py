"""Seed and accessor for the Community/Unowned system user.

Used by both the data migration that establishes the seed at deploy time and
by the `ensure_community_user` management command for local seeding / recovery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from apps.users.models import User


# The Community/Unowned user has a hardcoded UUID so callers can reference it
# by id without a DB roundtrip. The pattern of all-7s mirrors the sentinel
# kennitala (7777777777) and cannot collide with a real `uuid4()`.
COMMUNITY_USER_ID = UUID("77777777-7777-7777-7777-777777777777")
COMMUNITY_USER_KENNITALA = "7777777777"
COMMUNITY_USER_EMAIL = "community@naglasupan.is"
COMMUNITY_USER_INFO = (
    "Projects submitted by community members but owned by people outside of Naglasúpan."
)


def ensure_community_user(user_model: Any) -> User:
    user, created = user_model.objects.get_or_create(
        id=COMMUNITY_USER_ID,
        defaults={
            "email": COMMUNITY_USER_EMAIL,
            "kennitala": COMMUNITY_USER_KENNITALA,
            "is_system_user": True,
            "is_active": True,
            "is_verified": True,
            "info": COMMUNITY_USER_INFO,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def get_community_user() -> User:
    user_model = get_user_model()
    try:
        return user_model.objects.get(id=COMMUNITY_USER_ID)
    except user_model.DoesNotExist as exc:
        msg = (
            "Community/Unowned seed user not found. The seed migration may "
            "not have run."
        )
        raise RuntimeError(msg) from exc
