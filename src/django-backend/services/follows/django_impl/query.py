from uuid import UUID

from django.db.models import Prefetch, QuerySet

from apps.follows.models import Channel, Follow
from apps.projects.models import Project
from services.follows.query_interface import (
    ChannelFollowState,
    FollowQueryInterface,
    FollowState,
    FollowWithPreferences,
)
from services.project.django_impl.query import (
    project_gallery_images,
    resolve_image_by_purpose,
    variant_url,
)


def _follow_queryset(user_id: UUID) -> QuerySet[Follow]:
    """Everything `_to_follow_with_preferences` reads, in three queries.

    The project's channels and its gallery come off the prefetch rather than
    per follow — the Following page renders one row per follow, so anything
    fetched inside that loop is an N+1. The image prefetch is narrowed by
    `project_gallery_images()` because `resolve_image_by_purpose` does no
    filtering of its own and would otherwise fall back to an article upload or
    a row whose PUT never landed.
    """
    return (
        Follow.objects.filter(user_id=user_id)
        .select_related("project")
        .prefetch_related(
            "followed_channels",
            Prefetch(
                "project__channels",
                queryset=Channel.objects.order_by("created_at"),
            ),
            Prefetch("project__images", queryset=project_gallery_images()),
        )
    )


def _hero_image_url(project: Project) -> str | None:
    hero = resolve_image_by_purpose(project, "hero_banner")
    return variant_url(hero, "large")


def _to_follow_with_preferences(follow: Follow) -> FollowWithPreferences:
    followed_ids = {fc.channel_id for fc in follow.followed_channels.all()}
    channels = [
        ChannelFollowState(
            channel_id=channel.id,
            channel_name=channel.name,
            followed=channel.id in followed_ids,
        )
        for channel in follow.project.channels.all()
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
        follows = _follow_queryset(user_id).order_by("-created_at")
        return [_to_follow_with_preferences(f) for f in follows]

    def get_follow_preferences(
        self, user_id: UUID, project_slug: str
    ) -> FollowWithPreferences | None:
        follow = _follow_queryset(user_id).filter(project__slug=project_slug).first()
        if follow is None:
            return None
        return _to_follow_with_preferences(follow)
