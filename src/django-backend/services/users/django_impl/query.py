from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

from apps.articles.models import Article
from apps.projects.models import (
    Project,
    ProjectContributor,
    ProjectImage,
    ProjectStatus,
    UploadStatus,
)
from apps.users.models import UserAvatar
from apps.users.seed import COMMUNITY_USER_ID
from services.images.django_impl.query import gallery_prefetch
from services.project.django_impl.query import variant_url
from services.users.exceptions import UserNotFoundError
from services.users.query_interface import UserProjectItem, UserQueryInterface

# Maps a BroadcastEmail.email_type to the house-project channel whose
# per-user email preference now governs that broadcast. Replaces the legacy
# User.email_opt_in_* flags (dropped in add-article-authoring §9).
BROADCAST_CHANNEL_BY_EMAIL_TYPE = {
    "competition_results": "Competition Winners",
}

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from apps.users.models import User


def _main_image(project: Project) -> ProjectImage | None:
    """The cover, else the first gallery image — the listing card's rule.

    Reads the prefetched relation; `variant_url` then falls back to the
    original when the thumb has not been generated yet.
    """
    images = list(project.images.all())
    return next((img for img in images if img.is_main), None) or (
        images[0] if images else None
    )


class DjangoUserQuery(UserQueryInterface):
    def get_by_id(self, user_id: UUID) -> User:
        user_model = get_user_model()
        try:
            return user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            raise UserNotFoundError from None

    def get_active_by_id(self, user_id: UUID) -> User | None:
        user_model = get_user_model()
        try:
            user = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            return None
        if not user.is_active or user.is_system_user:
            return None
        return user

    def email_exists(self, email: str) -> bool:
        return get_user_model().objects.filter(email=email).exists()

    def kennitala_exists(self, kennitala: str) -> bool:
        return get_user_model().objects.filter(kennitala=kennitala).exists()

    def list_opted_in_for_broadcast_type(self, email_type: str) -> QuerySet:
        user_model = get_user_model()
        channel_name = BROADCAST_CHANNEL_BY_EMAIL_TYPE.get(email_type)
        if channel_name is None:
            return user_model.objects.none()
        house = Project.objects.filter(is_house_project=True).first()
        if house is None:
            return user_model.objects.none()
        return (
            user_model.objects.filter(
                is_active=True,
                is_system_user=False,
                follows__project=house,
                follows__followed_channels__channel__name=channel_name,
            )
            .exclude(article_email_frequency="never")
            .distinct()
        )

    def get_community_user(self) -> User:
        user_model = get_user_model()
        try:
            return user_model.objects.get(id=COMMUNITY_USER_ID)
        except user_model.DoesNotExist as exc:
            msg = (
                "Community/Unowned seed user not found. The seed migration may "
                "not have run."
            )
            raise RuntimeError(msg) from exc

    def get_pending_avatar(self, user: User, avatar_id: UUID) -> UserAvatar | None:
        return UserAvatar.objects.filter(
            pk=avatar_id, user=user, upload_status=UploadStatus.PENDING
        ).first()

    def list_public_projects_for(self, user_id: UUID) -> list[UserProjectItem]:
        rows = (
            ProjectContributor.objects.filter(
                user_id=user_id, project__status=ProjectStatus.APPROVED
            )
            .select_related("project__category")
            .prefetch_related(gallery_prefetch("project__images"), "project__tags")
            # "owner" < "tipster", so ascending puts what the person made
            # before what they pointed at.
            .order_by("role", "-project__published_at", "-project__created_at")
        )
        return [
            UserProjectItem(
                project=row.project,
                role=row.role,
                category_name=row.project.category.name
                if row.project.category
                else None,
                main_image_thumb_url=variant_url(_main_image(row.project), "thumb"),
            )
            for row in rows
        ]

    def list_public_articles_for(self, user_id: UUID) -> QuerySet[Article]:
        return (
            Article.objects.filter(
                author_id=user_id, project__status=ProjectStatus.APPROVED
            )
            .globally_visible()
            .select_related("channel", "project", "listing_image")
            .order_by("-published_at", "-created_at")
        )
