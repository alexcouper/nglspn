from uuid import UUID

from django.db import transaction

from apps.follows.models import Channel, Follow, FollowedChannel
from apps.projects.models import Project
from services.follows.exceptions import (
    ChannelNotOnProjectError,
    NotFollowingError,
)
from services.follows.handler_interface import FollowHandlerInterface
from services.follows.query_interface import ChannelFollowState, FollowState
from services.project.exceptions import ProjectNotFoundError


class DjangoFollowHandler(FollowHandlerInterface):
    def follow(self, user_id: UUID, project: Project) -> FollowState:
        # First follow auto-enrols every current channel. Re-following does
        # not enrol channels added after the original follow — that's the
        # user's choice to make via follow_channel().
        with transaction.atomic():
            follow, created = Follow.objects.get_or_create(
                user_id=user_id, project=project
            )
            if created:
                for channel in Channel.objects.filter(project=project):
                    FollowedChannel.objects.get_or_create(
                        follow=follow,
                        channel=channel,
                    )
        return FollowState(is_followed=True, created_at=follow.created_at)

    def unfollow(self, user_id: UUID, project: Project) -> None:
        Follow.objects.filter(user_id=user_id, project=project).delete()

    def _resolve(
        self, user_id: UUID, project_slug: str, channel_id: UUID
    ) -> tuple[Follow, Channel]:
        try:
            project = Project.objects.get(slug=project_slug)
        except Project.DoesNotExist as exc:
            raise ProjectNotFoundError from exc
        try:
            channel = Channel.objects.get(pk=channel_id, project=project)
        except Channel.DoesNotExist as exc:
            raise ChannelNotOnProjectError from exc
        try:
            follow = Follow.objects.get(user_id=user_id, project=project)
        except Follow.DoesNotExist as exc:
            raise NotFollowingError from exc
        return follow, channel

    def follow_channel(
        self, user_id: UUID, project_slug: str, channel_id: UUID
    ) -> ChannelFollowState:
        follow, channel = self._resolve(user_id, project_slug, channel_id)
        FollowedChannel.objects.get_or_create(follow=follow, channel=channel)
        return ChannelFollowState(
            channel_id=channel.id,
            channel_name=channel.name,
            followed=True,
        )

    def unfollow_channel(
        self, user_id: UUID, project_slug: str, channel_id: UUID
    ) -> None:
        follow, channel = self._resolve(user_id, project_slug, channel_id)
        FollowedChannel.objects.filter(follow=follow, channel=channel).delete()
