from uuid import UUID

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from ninja import Router

from api.schemas.errors import Error
from api.schemas.user import PublicUserProfile

User = get_user_model()
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
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 404, Error(detail="User not found")

    return user
