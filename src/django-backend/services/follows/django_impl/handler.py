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
        # First follow enrols every channel the project has now. Channels
        # added later are enrolled by the post_save receiver in
        # apps/follows/signals.py, so this loop only has to cover the ones
        # that predate the follow. Re-following writes nothing — `created` is
        # False — which leaves an unticked channel unticked, and a Follow left
        # with no channels at all empty until follow_channel() repairs it.
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
    ) -> FollowState:
        # Dropping the last channel is a full unfollow: this is the one path
        # where the user has just asked to stop. It does not make "no channels"
        # impossible — channel deletion cascades rows away, and two concurrent
        # calls here can each see the other's row as still present. See
        # handler_interface.unfollow_channel.
        with transaction.atomic():
            follow, channel = self._resolve(user_id, project_slug, channel_id)
            FollowedChannel.objects.filter(follow=follow, channel=channel).delete()
            if not FollowedChannel.objects.filter(follow=follow).exists():
                follow.delete()
                return FollowState(is_followed=False)
        return FollowState(is_followed=True, created_at=follow.created_at)
