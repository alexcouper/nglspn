from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 - needed at runtime for ninja path param

from django.http import HttpRequest
from ninja import Router

from api.auth.security import auth
from api.routers._helpers import get_optional_user
from api.routers.articles import can_view_hidden
from api.schemas.article import ArticleOut, UserArticleResponse
from api.schemas.errors import Error
from api.schemas.follow import FollowStateResponse
from api.schemas.user import UserProfileResponse, UserProjectResponse
from services import HANDLERS, REPO
from services.follows.exceptions import SelfFollowError

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
    about the page, not the schema. The follow endpoints share it: nobody can
    follow a person who has no page.
    """
    return REPO.users.get_active_by_id(user_id)


@router.get(
    "/{user_id}",
    response={200: UserProfileResponse, 404: Error},
    tags=["Users"],
)
def get_public_profile(
    request: HttpRequest,
    user_id: UUID,
) -> UserProfileResponse | tuple[int, Error]:
    user = _profile_user_or_none(user_id)
    if user is None:
        return NOT_FOUND
    viewer = get_optional_user(request)
    profile = UserProfileResponse.from_orm(user)
    profile.is_followed = REPO.follows.is_following_user(
        viewer.id if viewer else None, user.id
    )
    return profile


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


@router.get(
    "/{user_id}/articles/by-slug/{article_slug}",
    response={200: ArticleOut, 404: Error},
    tags=["Users"],
)
def get_author_article_by_slug(
    request: HttpRequest,
    user_id: UUID,
    article_slug: str,
) -> Article | tuple[int, Error]:
    """An author-owned article at its public address. Same draft and
    visibility rules as the project form: hidden ones 404 for everyone but the
    author."""
    if _profile_user_or_none(user_id) is None:
        return NOT_FOUND
    article = REPO.articles.get_by_author_and_slug(user_id, article_slug)
    if article is None:
        return 404, Error(detail="Article not found")
    if not article.is_globally_visible and not can_view_hidden(
        article, get_optional_user(request)
    ):
        return 404, Error(detail="Article not found")
    return article


@router.post(
    "/{user_id}/follow",
    response={200: FollowStateResponse, 400: Error, 401: Error, 404: Error},
    auth=auth,
    tags=["Follows"],
)
def follow_user(
    request: HttpRequest, user_id: UUID
) -> FollowStateResponse | tuple[int, Error]:
    person = _profile_user_or_none(user_id)
    if person is None:
        return NOT_FOUND
    try:
        state = HANDLERS.follows.follow_user(request.auth.id, person)
    except SelfFollowError:
        return 400, Error(detail="You cannot follow yourself")
    return FollowStateResponse(
        is_followed=state.is_followed, created_at=state.created_at
    )


@router.delete(
    "/{user_id}/follow",
    response={204: None, 401: Error, 404: Error},
    auth=auth,
    tags=["Follows"],
)
def unfollow_user(
    request: HttpRequest, user_id: UUID
) -> tuple[int, None] | tuple[int, Error]:
    person = _profile_user_or_none(user_id)
    if person is None:
        return NOT_FOUND
    HANDLERS.follows.unfollow_user(request.auth.id, person)
    return 204, None
