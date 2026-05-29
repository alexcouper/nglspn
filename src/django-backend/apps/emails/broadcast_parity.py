"""Pre/post-flip parity check for the broadcast recipient resolver.

Compares the legacy recipient set (``User.email_opt_in_*`` flags) against the
new Follow + FollowChannelPreference path, per broadcast ``email_type``. Run
this against a prod snapshot BEFORE dropping the legacy columns
(add-article-authoring §9) to confirm the flip does not change who receives
broadcasts.

Throwaway tooling: it reads the legacy columns directly, so it stops working
once §9 drops them — which is its intended lifetime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

from services.users.django_impl.query import DjangoUserQuery

if TYPE_CHECKING:
    from uuid import UUID

LEGACY_FLAG_BY_EMAIL_TYPE = {
    "competition_results": "email_opt_in_competition_results",
    "platform_updates": "email_opt_in_platform_updates",
}


@dataclass
class ParityResult:
    email_type: str
    only_legacy: set[UUID]
    only_new: set[UUID]

    @property
    def matches(self) -> bool:
        return not self.only_legacy and not self.only_new


def _legacy_recipient_ids(email_type: str) -> set[UUID]:
    flag = LEGACY_FLAG_BY_EMAIL_TYPE[email_type]
    return set(
        get_user_model()
        .objects.filter(is_active=True, is_system_user=False, **{flag: True})
        .values_list("id", flat=True)
    )


def _new_recipient_ids(email_type: str) -> set[UUID]:
    return set(
        DjangoUserQuery()
        .list_opted_in_for_broadcast_type(email_type)
        .values_list("id", flat=True)
    )


def check_parity(email_type: str) -> ParityResult:
    legacy = _legacy_recipient_ids(email_type)
    new = _new_recipient_ids(email_type)
    return ParityResult(
        email_type=email_type,
        only_legacy=legacy - new,
        only_new=new - legacy,
    )


def check_all() -> list[ParityResult]:
    return [check_parity(email_type) for email_type in LEGACY_FLAG_BY_EMAIL_TYPE]
