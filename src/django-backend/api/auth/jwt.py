from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import jwt
from django.conf import settings
from django.utils.crypto import constant_time_compare

from services import REPO

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


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


def create_refresh_token(
    user: "AbstractUser",
    *,
    auth_time: datetime | None = None,
) -> str:
    """Mint a refresh token for `user`.

    `auth_time` is the password login the session started with. A re-issue
    passes on what `verify_refresh_token` returned, so the absolute cap keeps
    counting from the original login; a login leaves it out.
    """
    now = datetime.now(tz=UTC)
    payload = {
        "user_id": str(user.id),
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
        "type": "refresh",
        "auth_time": int((auth_time or now).timestamp()),
        # Changes with the password, so a reset ends every other session.
        "pwv": user.get_session_auth_hash(),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


RESET_TOKEN_EXPIRE_MINUTES = 10


def create_reset_token(user_id: str) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "user_id": str(user_id),
        "exp": now + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "type": "reset",
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


def verify_refresh_token(token: str, user: "AbstractUser") -> datetime | None:
    """Return when the session behind `token` began, or None if it is over.

    A token is good for `user` while it is a refresh token of theirs, inside
    its idle expiry, inside the absolute cap, and minted under their current
    password.
    """
    payload = verify_token(token)
    if not payload or payload.get("type") != "refresh":
        return None

    if payload.get("user_id") != str(user.id):
        return None

    started = payload.get("auth_time")
    if started is None:
        return None

    auth_time = datetime.fromtimestamp(started, tz=UTC)
    absolute_lifetime = timedelta(days=settings.JWT_SESSION_ABSOLUTE_DAYS)
    if datetime.now(tz=UTC) - auth_time > absolute_lifetime:
        return None

    pwv = payload.get("pwv")
    if pwv is None or not constant_time_compare(pwv, user.get_session_auth_hash()):
        return None

    return auth_time


def get_user_from_token(token: str) -> "AbstractUser | None":
    payload = verify_token(token)
    if not payload:
        return None

    if payload.get("type") != "access":
        return None

    return REPO.users.get_active_by_id(UUID(payload["user_id"]))
