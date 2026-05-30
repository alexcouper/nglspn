from uuid import UUID

from apps.follows.models import Follow
from apps.projects.models import Project
from services.follows.query_interface import (
    ChannelFollowState,
    FollowQueryInterface,
    FollowState,
    FollowWithPreferences,
)
from services.project.django_impl.query import (
    resolve_image_by_purpose,
    variant_url,
)


def _hero_image_url(project: Project) -> str | None:
    hero = resolve_image_by_purpose(project, "hero_banner")
    return variant_url(hero, "large")


def _to_follow_with_preferences(follow: Follow) -> FollowWithPreferences:
    from apps.follows.models import Channel  # noqa: PLC0415

    followed_ids = {fc.channel_id for fc in follow.followed_channels.all()}
    channels = [
        ChannelFollowState(
            channel_id=channel.id,
            channel_name=channel.name,
            followed=channel.id in followed_ids,
        )
        for channel in Channel.objects.filter(project=follow.project).order_by(
            "created_at"
        )
    ]
    return FollowWithPreferences(
        project_slug=follow.project.slug or "",
        project_title=follow.project.title,
        project_hero_image_url=_hero_image_url(follow.project),
        created_at=follow.created_at,
        channels=channels,
    )


class DjangoFollowQuery(FollowQueryInterface):
    def is_followed(self, user_id: UUID | None, project: Project) -> bool:
        if user_id is None:
            return False
        return Follow.objects.filter(user_id=user_id, project=project).exists()

    def get_state(self, user_id: UUID | None, project: Project) -> FollowState:
        if user_id is None:
            return FollowState(is_followed=False)
        follow = Follow.objects.filter(user_id=user_id, project=project).first()
        if follow is None:
            return FollowState(is_followed=False)
        return FollowState(is_followed=True, created_at=follow.created_at)

    def list_user_follows(self, user_id: UUID) -> list[FollowWithPreferences]:
        follows = (
            Follow.objects.filter(user_id=user_id)
            .select_related("project")
            .prefetch_related("followed_channels")
            .order_by("-created_at")
        )
        return [_to_follow_with_preferences(f) for f in follows]

    def get_follow_preferences(
        self, user_id: UUID, project_slug: str
    ) -> FollowWithPreferences | None:
        follow = (
            Follow.objects.filter(user_id=user_id, project__slug=project_slug)
            .select_related("project")
            .prefetch_related("followed_channels")
            .first()
        )
        if follow is None:
            return None
        return _to_follow_with_preferences(follow)
