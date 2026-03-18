from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from apps.users.models import User


@dataclass(frozen=True)
class OnboardingStep:
    id: str
    priority: int
    check: Callable[[User], bool]


ONBOARDING_STEPS: list[OnboardingStep] = [
    OnboardingStep(
        id="verify-email",
        priority=100,
        check=lambda user: user.is_verified,
    ),
]
