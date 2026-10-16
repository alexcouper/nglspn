"""In-app helpers for the follows app.

Signals (auto-follow on user create, channel seed on project create) live here
too if they need cross-app helpers. The router-facing service layer lives under
`services/follows/` — see openspec change `add-project-following` §0 for the
architectural split.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.follows.models import Channel, Follow, FollowedChannel
from apps.projects.models import Project

logger = logging.getLogger(__name__)


def create_house_project_follow(user: "settings.AUTH_USER_MODEL") -> Follow | None:
    """Create a Follow on the house project for `user` and enrol each channel.

    Returns the Follow row, or None if no house project exists (greenfield dev
    DB case — logs a warning and no-ops).
    """
    house_project = Project.objects.filter(is_house_project=True).first()
    if house_project is None:
        logger.warning(
            "create_house_project_follow: no house project exists; "
            "skipping auto-follow for user %s",
            user.pk,
        )
        return None

    with transaction.atomic():
        follow, _created = Follow.objects.get_or_create(
            user=user, project=house_project
        )
        for channel in Channel.objects.filter(project=house_project):
            FollowedChannel.objects.get_or_create(
                follow=follow,
                channel=channel,
            )
    return follow


def anoint_house_project(project: Project) -> dict[str, int]:
    """Make `project` the house project and seed its broadcast plumbing.

    Demotes any current house project, flags this one, ensures the named
    broadcast channels exist, and backfills a Follow + FollowedChannel rows
    for every active, non-system user.

    Idempotent. In prod this state came from a data migration; this
    gives local dev and any fresh install the same starting point without
    replaying migrations.
    """
    from apps.projects.signals import DEFAULT_CHANNEL_NAME  # noqa: PLC0415
    from services.users.django_impl.query import (  # noqa: PLC0415
        BROADCAST_CHANNEL_BY_EMAIL_TYPE,
    )

    channel_names = [DEFAULT_CHANNEL_NAME, *BROADCAST_CHANNEL_BY_EMAIL_TYPE.values()]
    user_model = get_user_model()

    with transaction.atomic():
        Project.objects.filter(is_house_project=True).exclude(pk=project.pk).update(
            is_house_project=False
        )
        if not project.is_house_project:
            project.is_house_project = True
            project.save(update_fields=["is_house_project"])

        channels = [
            Channel.objects.get_or_create(project=project, name=name)[0]
            for name in channel_names
        ]

        eligible = user_model.objects.filter(is_active=True, is_system_user=False)
        follows_created = 0
        for user in eligible.iterator():
            follow, created = Follow.objects.get_or_create(user=user, project=project)
            follows_created += int(created)
            for channel in channels:
                FollowedChannel.objects.get_or_create(
                    follow=follow,
                    channel=channel,
                )

    return {
        "channels": len(channels),
        "eligible_users": eligible.count(),
        "follows_created": follows_created,
    }
