from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from ninja.security import HttpBearer

from .jwt import get_user_from_token

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

User = get_user_model()


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


def require_admin(user: "AbstractUser | None") -> bool:
    """Check if user is admin/superuser."""
    return bool(user and user.is_superuser)
