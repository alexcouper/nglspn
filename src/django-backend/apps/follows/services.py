"""In-app helpers for the follows app.

Signals (auto-follow on user create, channel seed on project create) live here
too if they need cross-app helpers. The router-facing service layer lives under
`services/follows/` — see openspec change `add-project-following` §0 for the
architectural split.
"""

import logging

from django.conf import settings
from django.db import transaction

from apps.follows.models import Channel, Follow, FollowChannelPreference
from apps.projects.models import Project

logger = logging.getLogger(__name__)


def create_house_project_follow(user: "settings.AUTH_USER_MODEL") -> Follow | None:
    """Create a Follow on the house project for `user`, with all-on prefs.

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
            FollowChannelPreference.objects.get_or_create(
                follow=follow,
                channel=channel,
                defaults={"email_enabled": True, "in_app_enabled": True},
            )
    return follow
