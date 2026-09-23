from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.models import (
        EmailVerificationCode,
        PasswordResetCode,
        User,
        UserAvatar,
    )
    from services.images.handler_interface import FileMeta, PreparedUpload


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

    @abstractmethod
    def create_avatar_upload(self, user: User, meta: FileMeta) -> PreparedUpload:
        """Reserve a `PENDING` avatar row and presign the PUT that fills it.

        Raises an `ImageError` subclass on a rejected type or size. Does not
        touch `user.avatar`: the reservation only becomes current on
        `complete_avatar_upload`.
        """

    @abstractmethod
    def complete_avatar_upload(
        self, user: User, avatar: UserAvatar, *, width: int | None, height: int | None
    ) -> User:
        """Make a reserved row the user's avatar once its object is in storage.

        Raises `UploadNotCompletedError` if the object is missing. The previously
        current row, if any, is deleted, which tombstones its object for the
        sweep.
        """

    @abstractmethod
    def remove_avatar(self, user: User) -> User:
        """Clear the user's avatar and delete its row. A no-op without one."""
