from typing import TYPE_CHECKING

from django.http import HttpRequest
from ninja.security import HttpBearer

from .jwt import get_user_from_token

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class JWTAuth(HttpBearer):
    def authenticate(
        self,
        request: HttpRequest,
        token: str,
    ) -> "AbstractUser | None":
        user = get_user_from_token(token)
        if user:
            return user
        return None


# Instance to use in endpoints
auth = JWTAuth()


MODERATOR_GROUP_NAME = "MODERATOR"


def require_admin(user: "AbstractUser | None") -> bool:
    """Check if user is admin/superuser."""
    return bool(user and user.is_superuser)


def require_moderator(user: "AbstractUser | None") -> tuple[int, dict] | None:
    """Check if user is a moderator or superuser.

    Returns None if authorized, or a (status_code, error_dict) tuple if not.
    """
    if not user:
        return 401, {"detail": "Authentication required"}
    if user.is_superuser:
        return None
    if user.groups.filter(name=MODERATOR_GROUP_NAME).exists():
        return None
    return 403, {"detail": "Moderator access required"}
