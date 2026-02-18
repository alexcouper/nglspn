from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.models import EmailVerificationCode, User


@dataclass
class RegisterUserInput:
    email: str
    password: str
    kennitala: str
    first_name: str
    last_name: str


class UserHandlerInterface(ABC):
    @abstractmethod
    def register(self, data: RegisterUserInput) -> User: ...

    @abstractmethod
    def create_verification_code(
        self, user: User, expires_minutes: int
    ) -> EmailVerificationCode: ...

    @abstractmethod
    def verify_code(self, user: User, code: str) -> bool: ...
