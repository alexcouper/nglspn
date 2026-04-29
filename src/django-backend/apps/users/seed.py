"""Constants and seed helper for the Community/Unowned system user.

The constants are imported by the runtime (services, handler) for foreign-key
references. `ensure_community_user` is the idempotent writer used by the
management command for local seeding / recovery; the data migration in
`migrations/0015_community_user_seed.py` keeps its own inline copy of the
literal values to remain frozen against future edits to this module.

Runtime read access goes through `REPO.users.get_community_user()`, not this
module — this file deliberately holds no query helper so apps/ stays free of
service-layer logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

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
