from __future__ import annotations

from typing import TYPE_CHECKING

from services.registration.handler_interface import RegistrationHandlerInterface
from services.registration.steps import ONBOARDING_STEPS

if TYPE_CHECKING:
    from apps.users.models import User
    from services.registration.steps import OnboardingStep


class DjangoRegistrationHandler(RegistrationHandlerInterface):
    def get_pending_steps(self, user: User) -> list[OnboardingStep]:
        pending = [step for step in ONBOARDING_STEPS if not step.check(user)]
        return sorted(pending, key=lambda s: s.priority)
