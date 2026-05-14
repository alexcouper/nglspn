from uuid import UUID

from django.db import transaction

from apps.follows.models import Channel, Follow, FollowChannelPreference
from apps.projects.models import Project
from apps.users.models import User
from services.follows.exceptions import (
    ChannelNotOnProjectError,
    EmptyPatchError,
    NotFollowingError,
)
from services.follows.handler_interface import FollowHandlerInterface
from services.follows.query_interface import ChannelPreferenceState, FollowState
from services.project.exceptions import ProjectNotFoundError

LEGACY_FLAG_BY_CHANNEL_NAME = {
    "Competition Winners": "email_opt_in_competition_results",
    "Product Updates": "email_opt_in_platform_updates",
}


def _mirror_legacy_email_flag(
    user: User, channel: Channel, *, email_enabled: bool
) -> None:
    if not channel.project.is_house_project:
        return
    flag = LEGACY_FLAG_BY_CHANNEL_NAME.get(channel.name)
    if flag is None:
        return
    setattr(user, flag, email_enabled)
    user.save(update_fields=[flag])


def _clear_legacy_email_flags(user: User) -> None:
    user.email_opt_in_competition_results = False
    user.email_opt_in_platform_updates = False
    user.save(
        update_fields=[
            "email_opt_in_competition_results",
            "email_opt_in_platform_updates",
        ]
    )


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
        with transaction.atomic():
            deleted, _ = Follow.objects.filter(
                user_id=user_id, project=project
            ).delete()
            if deleted and project.is_house_project:
                user = User.objects.get(pk=user_id)
                _clear_legacy_email_flags(user)

    def set_channel_preference(
        self,
        user_id: UUID,
        project_slug: str,
        channel_id: UUID,
        *,
        email_enabled: bool | None = None,
        in_app_enabled: bool | None = None,
    ) -> ChannelPreferenceState:
        if email_enabled is None and in_app_enabled is None:
            raise EmptyPatchError

        try:
            project = Project.objects.get(slug=project_slug)
        except Project.DoesNotExist as exc:
            raise ProjectNotFoundError from exc

        try:
            channel = Channel.objects.select_related("project").get(
                pk=channel_id, project=project
            )
        except Channel.DoesNotExist as exc:
            raise ChannelNotOnProjectError from exc

        try:
            follow = Follow.objects.get(user_id=user_id, project=project)
        except Follow.DoesNotExist as exc:
            raise NotFollowingError from exc

        try:
            preference = FollowChannelPreference.objects.get(
                follow=follow, channel=channel
            )
        except FollowChannelPreference.DoesNotExist as exc:
            # A Follow always has prefs for every channel of its project
            # (POST creates them). A missing row here means the data model
            # was violated; surface as a not-following-style 404.
            raise NotFollowingError from exc

        with transaction.atomic():
            updates: list[str] = []
            if email_enabled is not None:
                preference.email_enabled = email_enabled
                updates.append("email_enabled")
            if in_app_enabled is not None:
                preference.in_app_enabled = in_app_enabled
                updates.append("in_app_enabled")
            preference.save(update_fields=updates)

            if email_enabled is not None:
                user = User.objects.get(pk=user_id)
                _mirror_legacy_email_flag(user, channel, email_enabled=email_enabled)

        return ChannelPreferenceState(
            channel_id=channel.id,
            channel_name=channel.name,
            email_enabled=preference.email_enabled,
            in_app_enabled=preference.in_app_enabled,
        )
