from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.models import User
    from services.registration.steps import OnboardingStep


class RegistrationHandlerInterface(ABC):
    @abstractmethod
    def get_pending_steps(self, user: User) -> list[OnboardingStep]: ...
