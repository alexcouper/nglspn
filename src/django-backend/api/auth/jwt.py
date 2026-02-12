from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

User = get_user_model()


def create_access_token(user_id: str) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "user_id": str(user_id),
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "type": "access",
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "user_id": str(user_id),
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_from_token(token: str) -> "AbstractUser | None":
    payload = verify_token(token)
    if not payload:
        return None

    try:
        user = User.objects.get(id=payload["user_id"])
    except User.DoesNotExist:
        return None
    else:
        return user if user.is_active else None
