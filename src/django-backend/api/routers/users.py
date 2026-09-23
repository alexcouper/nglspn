from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 - needed at runtime for ninja path param

from django.http import HttpRequest
from ninja import Router

from api.schemas.article import UserArticleResponse
from api.schemas.errors import Error
from api.schemas.user import PublicUserProfile, UserProjectResponse
from services import REPO

if TYPE_CHECKING:
    from apps.articles.models import Article
    from apps.users.models import User

router = Router()

NOT_FOUND = (404, Error(detail="User not found"))


def _profile_user_or_none(user_id: UUID) -> User | None:
    """The user behind a public profile, or None.

    `get_active_by_id` excludes inactive accounts and system users. Neither
    has a page: the UI already refuses to link to a system user, and an account
    that cannot log in should not be browsable either. The embedded
    `PublicUserProfile` on projects and articles is unaffected — this rule is
    about the page, not the schema.
    """
    return REPO.users.get_active_by_id(user_id)


@router.get(
    "/{user_id}",
    response={200: PublicUserProfile, 404: Error},
    tags=["Users"],
)
def get_public_profile(
    request: HttpRequest,
    user_id: UUID,
) -> User | tuple[int, Error]:
    user = _profile_user_or_none(user_id)
    if user is None:
        return NOT_FOUND
    return user


@router.get(
    "/{user_id}/projects",
    response={200: list[UserProjectResponse], 404: Error},
    tags=["Users"],
)
def list_public_projects(
    request: HttpRequest,
    user_id: UUID,
) -> list[UserProjectResponse] | tuple[int, Error]:
    if _profile_user_or_none(user_id) is None:
        return NOT_FOUND
    return [
        UserProjectResponse.from_item(item)
        for item in REPO.users.list_public_projects_for(user_id)
    ]


@router.get(
    "/{user_id}/articles",
    response={200: list[UserArticleResponse], 404: Error},
    tags=["Users"],
)
def list_public_articles(
    request: HttpRequest,
    user_id: UUID,
) -> list[Article] | tuple[int, Error]:
    if _profile_user_or_none(user_id) is None:
        return NOT_FOUND
    return list(REPO.users.list_public_articles_for(user_id))
