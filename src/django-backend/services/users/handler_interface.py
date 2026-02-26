from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.models import EmailVerificationCode, PasswordResetCode, User


@dataclass
class RegisterUserInput:
    email: str
    password: str
    kennitala: str
    first_name: str
    last_name: str


@dataclass
class VerifyResetCodeResult:
    user: User | None
    attempts_remaining: int


class UserHandlerInterface(ABC):
    @abstractmethod
    def register(self, data: RegisterUserInput) -> User: ...

    @abstractmethod
    def create_verification_code(
        self, user: User, expires_minutes: int
    ) -> EmailVerificationCode: ...

    @abstractmethod
    def verify_code(self, user: User, code: str) -> bool: ...

    @abstractmethod
    def create_password_reset_code(
        self, email: str, expires_minutes: int
    ) -> PasswordResetCode | None: ...

    @abstractmethod
    def verify_password_reset_code(
        self, email: str, code: str
    ) -> VerifyResetCodeResult: ...

    @abstractmethod
    def reset_password(self, user: User, new_password: str) -> None: ...
