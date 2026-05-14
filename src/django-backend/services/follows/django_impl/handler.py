from uuid import UUID

from django.db import transaction

from apps.follows.models import Channel, Follow, FollowChannelPreference
from apps.projects.models import Project
from services.follows.handler_interface import FollowHandlerInterface
from services.follows.query_interface import FollowState


class DjangoFollowHandler(FollowHandlerInterface):
    def follow(self, user_id: UUID, project: Project) -> FollowState:
        with transaction.atomic():
            follow, _created = Follow.objects.get_or_create(
                user_id=user_id, project=project
            )
            for channel in Channel.objects.filter(project=project):
                FollowChannelPreference.objects.get_or_create(
                    follow=follow,
                    channel=channel,
                    defaults={"email_enabled": True, "in_app_enabled": True},
                )
        return FollowState(is_followed=True, created_at=follow.created_at)

    def unfollow(self, user_id: UUID, project: Project) -> None:
        # Hard-delete; FollowChannelPreference cascades.
        Follow.objects.filter(user_id=user_id, project=project).delete()
