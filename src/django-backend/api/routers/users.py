from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 - needed at runtime for ninja path param

from django.http import HttpRequest
from ninja import Router

from api.schemas.errors import Error
from api.schemas.user import PublicUserProfile
from services import REPO
from services.users.exceptions import UserNotFoundError

if TYPE_CHECKING:
    from apps.users.models import User

router = Router()


@router.get(
    "/{user_id}",
    response={200: PublicUserProfile, 404: Error},
    tags=["Users"],
)
def get_public_profile(
    request: HttpRequest,
    user_id: UUID,
) -> User | tuple[int, Error]:
    try:
        user = REPO.users.get_by_id(user_id)
    except UserNotFoundError:
        return 404, Error(detail="User not found")

    return user
